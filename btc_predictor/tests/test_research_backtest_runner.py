"""RBT-007 ``RUN_FIRST_RESEARCH_BACKTEST_V1``: the runner, the shared results, the audit and the report.

Every test is synthetic: the RBT-004/RBT-005 composer worlds, the committed
preregistration and throwaway directories. No real-data value is read or
computed, and nothing touches the private store, the holdout or BTC-019.
"""

from __future__ import annotations

import contextlib
import copy
import gzip
import hashlib
import json
import shutil
import pickle
import subprocess
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from btc_predictor.backtest.costs import cost_profile
from btc_predictor.research_backtest import entry_composer as ec
from btc_predictor.research_backtest import runner as rn
from btc_predictor.research_backtest import runner_metrics as rm
from btc_predictor.research_backtest import runner_report as rr
from btc_predictor.research_backtest import runner_shared as rs
from btc_predictor.research_backtest.replay_inputs import COINBASE_REPLAY_VENUE, canonical_json_bytes
from btc_predictor.tests.rbt004_composer_fixtures import CONFIG, DAY, Scenario, utc
from btc_predictor.tests.rbt005_management_fixtures import management_market

REPOSITORY = Path(__file__).resolve().parents[2]
START, LAST = utc(2024, 3, 25), utc(2024, 4, 18)
SCHEDULE = tuple(utc(2024, 3, 10) + DAY * index for index in range(40))
SYNTHETIC_FOLD_BARS = 24 * 7


# --- fixtures ----------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def preregistration():
    return rn.read_preregistration(REPOSITORY)


@pytest.fixture(scope="module")
def markets():
    return {
        "BITSTAMP": management_market(end=utc(2024, 4, 20)).build(),
        "COINBASE": management_market(end=utc(2024, 4, 20), venue=COINBASE_REPLAY_VENUE).build(),
    }


def _registry(preregistration):
    registry = rn.Registry(champion=CONFIG)
    registry.add(rn.Variant(rn.CHAMPION, CONFIG, "CHAMPION"))
    for variant in rn.sweep_variants(preregistration["threshold_sweeps"]["sweeps"], CONFIG):
        if variant.sweep_index == 0:
            registry.add(variant)
    registry.add(rn.ablation_variant(preregistration["ablation"], CONFIG))
    return registry


GOLDEN = {
    "synthetic_golden": {
        "scenario_id": "synthetic_golden",
        "period": {"start": "2024-03-29", "end": "2024-04-05"},
        "cost_profile": "base",
        "starting_nav": "1000000",
        "plan": {"decisions": [{"on": "2024-03-30", "action": "ARM_ENTRY"}]},
    }
}


@pytest.fixture(scope="module")
def share_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("shared")


@pytest.fixture(scope="module")
def share(markets, share_dir):
    encoder = rs.ArgumentEncoder()
    for inputs in markets.values():
        rs.register_positioning_sources(encoder, inputs)
    store = rs.SharedResultStore(share_dir)
    return lambda: rs.shared_positioning(store, encoder)


@pytest.fixture(scope="module")
def context(markets, preregistration, share):
    with share():
        history = {"BITSTAMP": rn.continuous_history(markets["BITSTAMP"], CONFIG, LAST, SCHEDULE)}
    return rn.RunContext(
        inputs={"BITSTAMP": markets["BITSTAMP"]},
        registry=_registry(preregistration),
        evaluation={"BITSTAMP": (START, LAST)},
        golden=GOLDEN,
        fold_bars=SYNTHETIC_FOLD_BARS,
        history=history,
        schedule=SCHEDULE,
    )


@pytest.fixture(scope="module")
def headline(context, share):
    with share():
        return rn.execute_run(rn.RunSpec(rn.HEADLINE, "BITSTAMP", rn.CHAMPION, "base"), context, record_management=True)


@pytest.fixture(scope="module")
def walk_forward(context, share):
    with share():
        return rn.execute_run(rn.RunSpec(rn.WALK_FORWARD, "BITSTAMP", rn.CHAMPION, "base"), context)


# --- the shared positioning results (the runtime ruling, ruling 6) -------------------------------


def test_the_share_covers_the_four_public_owners_and_ruling_6s_helpers():
    assert rs.SHARED_PUBLIC_FUNCTIONS == ("funding_health", "futures_basis_health", "open_interest_growth_health", "open_interest_intensity")
    assert set(rs.SHARED_HELPER_FUNCTIONS) == {
        "_open_interest_growth_by_time",
        "_funding_averages_by_time",
        "_futures_basis_averages_by_time",
        "_aggregate_open_interest_by_time",
    }


def test_rows_key_by_source_content_and_position(markets):
    a, b = markets["BITSTAMP"].dataset.shared_snapshot.funding_rates, markets["COINBASE"].dataset.shared_snapshot.funding_rates
    assert a == b and a is not b
    encoder = rs.ArgumentEncoder()
    assert encoder.register_source(a) == encoder.register_source(b)
    key = encoder.key("funding_health", (a[:50],), {"as_of": utc(2024, 3, 1)})
    assert encoder.key("funding_health", (b[:50],), {"as_of": utc(2024, 3, 1)}) == key
    assert encoder.key("funding_health", (a[:49],), {"as_of": utc(2024, 3, 1)}) != key
    assert encoder.key("funding_health", (tuple(reversed(a[:50])),), {"as_of": utc(2024, 3, 1)}) != key
    assert encoder.key("funding_health", (a[:50],), {"as_of": utc(2024, 3, 2)}) != key
    assert encoder.key("funding_averages", (a[:50],), {"as_of": utc(2024, 3, 1)}) != key


def test_keys_keep_decimal_exponents_and_mapping_order():
    encoder = rs.ArgumentEncoder()
    assert encoder.key("f", (Decimal("1.0"),), {}) != encoder.key("f", (Decimal("1.00"),), {})
    first = {utc(2024, 1, 1): Decimal("1"), utc(2024, 1, 2): Decimal("2")}
    second = dict(reversed(list(first.items())))
    assert first == second
    assert encoder.key("f", (first,), {}) != encoder.key("f", (second,), {})
    assert encoder.key("f", (first,), {}) == encoder.key("f", (dict(first),), {})


def test_an_unregistered_row_or_a_naive_time_is_never_shared(markets):
    encoder = rs.ArgumentEncoder()
    rows = markets["BITSTAMP"].dataset.shared_snapshot.funding_rates
    with pytest.raises(rs.Unencodable):
        encoder.key("funding_health", (rows[:3],), {})
    with pytest.raises(rs.Unencodable):
        encoder.key("f", (utc(2024, 1, 1).replace(tzinfo=None),), {})
    encoder.register_source(rows)
    copies = tuple(replace(row) for row in rows[:3])
    assert copies == rows[:3]
    with pytest.raises(rs.Unencodable):  # equal values, but not the source's objects
        encoder.key("funding_health", (copies,), {})


def test_the_store_serves_fresh_copies_and_refuses_another_keys_file(tmp_path):
    store = rs.SharedResultStore(tmp_path, memory_entries=1)
    store.put("a" * 64, "f", {"x": [1, 2]})
    served = store.get("a" * 64, "f")
    served["x"].append(3)
    assert store.get("a" * 64, "f") == {"x": [1, 2]}
    assert store.get("b" * 64, "f") is rs.MISSING
    with pytest.raises(rs.SharedPositioningError):
        store.get("a" * 64, "g")
    other = rs.SharedResultStore(tmp_path / "other")
    other.put("c" * 64, "f", 1)
    (tmp_path / "other" / "dd").mkdir()
    source = tmp_path / "other" / "cc" / ("c" * 64 + ".pickle")
    target = tmp_path / "other" / "dd" / ("d" * 64 + ".pickle")
    target.write_bytes(source.read_bytes())
    with pytest.raises(rs.SharedPositioningError):
        rs.SharedResultStore(tmp_path / "other").get("d" * 64, "f")


def test_shared_results_give_byte_identical_ledgers_across_venues(markets, tmp_path):
    first, last = utc(2024, 3, 28), utc(2024, 3, 31)

    def ledger(inputs):
        composer = ec.EntryComposer(inputs, strategy_config=CONFIG)
        instant = first
        while instant <= last:
            composer.record(composer.decide(instant))
            instant += DAY
        return composer.ledger_bytes()

    plain = {venue: ledger(inputs) for venue, inputs in markets.items()}
    encoder = rs.ArgumentEncoder()
    for inputs in markets.values():
        rs.register_positioning_sources(encoder, inputs)
    originals = {name: getattr(ec, name) for name in rs.SHARED_FUNCTIONS}
    with rs.shared_positioning(rs.SharedResultStore(tmp_path), encoder) as stats:
        shared = {venue: ledger(inputs) for venue, inputs in markets.items()}
    assert shared == plain
    assert {name: getattr(ec, name) for name in rs.SHARED_FUNCTIONS} == originals
    record = stats.as_record()
    assert all(entry["not_shared"] == 0 for entry in record.values())
    # the second venue is served entirely from the first venue's results
    assert all(entry["served"] >= entry["computed"] > 0 for entry in record.values())


def test_a_misbound_name_refuses_the_share(tmp_path, monkeypatch):
    monkeypatch.setattr(ec, "funding_health", lambda *args, **kwargs: None)
    with pytest.raises(rs.SharedPositioningError):
        with rs.shared_positioning(rs.SharedResultStore(tmp_path), rs.ArgumentEncoder()):
            pass


def test_an_unencodable_call_reaches_the_owner_unshared(markets, tmp_path):
    rows = markets["BITSTAMP"].dataset.shared_snapshot.funding_rates
    with rs.shared_positioning(rs.SharedResultStore(tmp_path), rs.ArgumentEncoder()) as stats:
        result = ec.funding_health(rows, as_of=utc(2024, 3, 1))
    assert result == rs.positioning.funding_health(rows, as_of=utc(2024, 3, 1))
    assert stats.not_shared["funding_health"] == 1 and stats.computed["funding_health"] == 0


# --- the variants and the registry (ruling 2) ------------------------------------------------------


def test_the_sweep_variants_are_the_preregistered_candidates(preregistration):
    variants = rn.sweep_variants(preregistration["threshold_sweeps"]["sweeps"], CONFIG)
    swept = [record for record in preregistration["threshold_sweeps"]["sweeps"] if record["status"] == "SWEPT"]
    assert len(variants) == sum(len(record["candidate_values"]) for record in swept) == 68
    base = rn.prereg._configuration_mapping()
    for variant in variants:
        record = preregistration["threshold_sweeps"]["sweeps"][variant.sweep_index]
        value = Decimal(variant.value)
        assert value in {Decimal(item) for item in record["candidate_values"]}
        assert variant.config.run_metadata()["parameter_set_id"] == variant.variant_id
        assert rn.prereg._candidate_refusal(base, record["parameter"], record["parameter_paths"], value) is None
        updates = {path: rn._configured_number(base, path, value) for path in record["parameter_paths"]}
        assert rn._with_paths(base, updates, variant.variant_id) == variant.config
        unchanged = rn._with_paths(base, {}, variant.variant_id)
        assert (variant.config == unchanged) == (value == Decimal(record["configured_value"]))


def test_the_ablation_variant_holds_the_frozen_weights(preregistration):
    variant = rn.ablation_variant(preregistration["ablation"], CONFIG)
    weights = {key: Decimal(str(value)) for key, value in variant.config.scoring_weights.hold_score.items()}
    assert weights == {key: Decimal(value) for key, value in preregistration["ablation"]["variant_weights"].items()}
    assert weights["momentum_persistence"] == 0
    tampered = copy.deepcopy(preregistration["ablation"])
    tampered["variant_weights"]["trend"] = "0.3"
    with pytest.raises(rn.RunnerRefused, match="ABLATION_REFUSED"):
        rn.ablation_variant(tampered, CONFIG)


def test_only_a_registered_configuration_reaches_the_composer(context, markets):
    registered = next(variant for variant in context.registry.variants.values() if variant.role == rn.SWEEP)
    copy_of = rn.Variant(registered.variant_id, registered.config, registered.role)
    with pytest.raises(rn.RunnerRefused, match="REGISTRY_REFUSED"):
        rn.RegisteredEntryComposer(markets["BITSTAMP"], variant=copy_of, registry=context.registry)
    composer = rn.RegisteredEntryComposer(markets["BITSTAMP"], variant=registered, registry=context.registry)
    assert composer.strategy_config is registered.config
    decision = composer.decide(utc(2024, 3, 31))
    assert decision.composition.run.results["regime_classification"].config_metadata == registered.config.run_metadata()
    champion = rn.RegisteredEntryComposer(markets["BITSTAMP"], variant=context.registry.variants[rn.CHAMPION], registry=context.registry)
    assert champion.strategy_config is CONFIG


# --- the frozen inputs and code (ruling 2) ----------------------------------------------------------


def test_the_preregistration_must_match_its_digest(tmp_path):
    directory = tmp_path / rn.prereg.ARTIFACT_DIRECTORY
    directory.mkdir(parents=True)
    data = (REPOSITORY / rn.PREREGISTRATION_PATH).read_bytes()
    (tmp_path / rn.PREREGISTRATION_PATH).write_bytes(data)
    (tmp_path / rn.PREREGISTRATION_DIGEST_PATH).write_bytes((REPOSITORY / rn.PREREGISTRATION_DIGEST_PATH).read_bytes())
    assert rn.read_preregistration(tmp_path)["code_commit"].startswith("2be45ad")
    (tmp_path / rn.PREREGISTRATION_PATH).write_bytes(data.replace(b'"base"', b'"BASE"', 1))
    with pytest.raises(rn.RunnerRefused, match="PREREGISTRATION_REFUSED"):
        rn.read_preregistration(tmp_path)


def test_every_frozen_choice_rederives_and_tampering_refuses(preregistration):
    rn.verify_preregistration(preregistration, CONFIG)
    for path, value in (
        (("threshold_sweeps", "sweeps", 0, "candidate_values"), ["72"]),
        (("cost_ladder", "rungs", "base", "fee_bps"), "1"),
        (("decision_schedule", "instants"), 2190),
        (("report", "metric_spec_sha256"), "0" * 64),
    ):
        tampered = copy.deepcopy(preregistration)
        node = tampered
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        with pytest.raises(rn.RunnerRefused, match="PREREGISTRATION_REFUSED"):
            rn.verify_preregistration(tampered, CONFIG)


def test_the_frozen_code_check_finds_a_changed_or_missing_file(tmp_path):
    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    git("init", "-q")
    (tmp_path / "a.py").write_text("one\n")
    (tmp_path / "b.py").write_text("two\n")
    git("add", ".")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c")
    commit = subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    assert rn.frozen_code_mismatches(tmp_path, commit, ["a.py", "b.py"]) == []
    (tmp_path / "b.py").write_text("changed\n")
    (tmp_path / "c.py").write_text("new\n")
    assert rn.frozen_code_mismatches(tmp_path, commit, ["a.py", "b.py", "c.py"]) == ["b.py", "c.py"]


def test_the_loaded_repository_code_is_the_frozen_commit(preregistration):
    import sys

    paths = rn.frozen_code_paths(REPOSITORY, list(sys.modules.items()))
    assert "btc_predictor/research_backtest/entry_composer.py" in paths
    assert "btc_predictor/research_backtest/management_composer.py" in paths
    assert "btc_predictor/features/positioning.py" in paths
    assert rn.STRATEGY_CONFIG_PATH.as_posix() in paths and rn.GOLDEN_FIXTURE_PATH.as_posix() in paths
    assert not any((path.startswith("btc_predictor/tests/") and path.endswith(".py")) or Path(path).name in rn.RUNNER_MODULES for path in paths)
    assert rn.frozen_code_mismatches(REPOSITORY, preregistration["code_commit"], paths) == []


def _module(name, origin, loader_type=None, cached=None):
    import importlib.machinery
    import importlib.util
    import types

    module = types.ModuleType(name)
    loader = (loader_type or importlib.machinery.SourceFileLoader)(name, str(origin))
    module.__spec__ = importlib.util.spec_from_loader(name, loader, origin=str(origin))
    module.__spec__.cached = cached
    module.__file__ = str(origin)
    return module


def test_a_repository_module_not_loaded_from_its_source_refuses(tmp_path):
    import importlib.machinery

    owner = REPOSITORY / "btc_predictor" / "features" / "positioning.py"
    assert rn.frozen_code_paths(REPOSITORY, [("btc_predictor.features.positioning", _module("btc_predictor.features.positioning", owner))]) == sorted(
        ["btc_predictor/features/positioning.py", rn.STRATEGY_CONFIG_PATH.as_posix(), rn.GOLDEN_FIXTURE_PATH.as_posix()]
    )
    elsewhere = tmp_path / "positioning.py"
    elsewhere.write_text("VALUE = 1\n")
    cases = [
        _module("btc_predictor.features.positioning", elsewhere),
        _module("btc_predictor.features.positioning", owner.with_suffix(".pyc"), importlib.machinery.SourcelessFileLoader),
        # another loader reporting the real .py file as its origin (an import hook that runs other code)
        _module("btc_predictor.features.positioning", owner, importlib.machinery.SourcelessFileLoader),
        _module("btc_predictor.features.positioning", owner, cached=str(tmp_path / "stale" / "positioning.cpython-312.pyc")),
        # review RR3: a source loader subclass reporting the real origin may change the code it loads
        _module("btc_predictor.features.positioning", owner, type("Transforming", (importlib.machinery.SourceFileLoader,), {})),
    ]
    for module in cases:
        with pytest.raises(rn.RunnerRefused, match="FROZEN_CODE_REFUSED"):
            rn.frozen_code_paths(REPOSITORY, [(module.__name__, module)], pycache_prefix=str(tmp_path / "fresh"))
    # the runner's own modules are checked for their loader too, though not against the frozen commit
    runner = _module("btc_predictor.research_backtest.runner", elsewhere)
    with pytest.raises(rn.RunnerRefused, match="FROZEN_CODE_REFUSED"):
        rn.frozen_code_paths(REPOSITORY, [(runner.__name__, runner)])
    assert rn.frozen_code_paths(REPOSITORY, [("numpy", _module("numpy", elsewhere))]) == sorted([rn.STRATEGY_CONFIG_PATH.as_posix(), rn.GOLDEN_FIXTURE_PATH.as_posix()])


LAUNCHER = REPOSITORY / rn.LAUNCHER


def _launched(args, tmp_path, environment=None, shell=()):
    """The committed launcher itself, started as the owner starts it (by its first line), with this interpreter and a private TMPDIR."""

    import os
    import sys

    temporary = tmp_path / "launcher-tmp"
    temporary.mkdir(exist_ok=True)
    variables = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "TMPDIR": str(temporary), "RBT007_PYTHON": sys.executable}
    return subprocess.run([*shell, str(LAUNCHER), *args], env={**variables, **(environment or {})}, capture_output=True, text=True, check=False)


def _entry_command(args, prefix, drop=()):
    """The launcher's own interpreter command and entry, for the variants the launcher never makes."""

    import sys

    entry = LAUNCHER.read_text().split("entry='", 1)[1].split("'\n", 1)[0]
    command = [sys.executable, "-I", "-S", "-B", "-X", f"pycache_prefix={prefix}", "-c", entry, str(REPOSITORY), *args]
    return [part for part in command if part not in drop]


def _entry_environment(prefix, **extra):
    """The environment the launcher gives its interpreter (review Q1)."""

    import os

    return {"PATH": os.confstr("CS_PATH"), **rn.LAUNCH_GIT_ENVIRONMENT, rn.FRESH_BYTECODE_ENV: str(prefix), **extra}


_LAUNCHED_ENVIRONMENT = {"PATH", "TMPDIR", "GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL", rn.FRESH_BYTECODE_ENV}


def test_the_launcher_starts_the_command_isolated_with_a_fresh_bytecode_cache(tmp_path):
    import os

    # review N2: the command's process is started by the committed launcher, never by an ordinary interpreter
    assert not rn.fresh_bytecode_process()
    with pytest.raises(rn.RunnerRefused, match="FROZEN_CODE_REFUSED"):
        rn.require_fresh_bytecode()
    text = LAUNCHER.read_text()
    assert os.access(LAUNCHER, os.X_OK) and "command -p env -i " in text and f'"{rn.FRESH_BYTECODE_ENV}=$cache"' in text
    assert '"$python" -I -S -B -X "pycache_prefix=$cache" -c "$entry" "$repository" "$@"' in text
    shown = _launched(["--help"], tmp_path)
    assert shown.returncode == 0 and shown.stdout.startswith("usage: runner"), shown.stdout + shown.stderr
    # in its process every repository module was compiled from its source into the new, empty cache, then removed
    checked = _launched(["preflight"], tmp_path, {"RBT007_PROBE_INHERITED": "1"})
    assert checked.returncode == 0, checked.stdout + checked.stderr
    report = json.loads(checked.stdout)
    assert report["launched"] is True and report["modules_from_source"] > 50 and report["path"][0] == str(REPOSITORY)
    # only the launcher's own variables reach it: not the interpreter's name, nor HOME, nor anything else the
    # caller had (under the C locale the interpreter sets LC_CTYPE itself, PEP 538)
    assert set(report["environment"]) - {"LC_CTYPE"} == _LAUNCHED_ENVIRONMENT
    # each launch's cache is a new private directory, never a name another process could know or fill first
    again = json.loads(_launched(["preflight"], tmp_path).stdout)
    caches = [Path(item["cache"]["path"]) for item in (report, again)]
    assert caches[0] != caches[1] and {item["cache"]["mode"] for item in (report, again)} == {"0o700"}
    assert all(cache.parent == tmp_path / "launcher-tmp" and cache.name.startswith("rbt007-pycache-") for cache in caches)
    assert not any((tmp_path / "launcher-tmp").iterdir())
    # a cache that already holds anything is refused; without -I or -S the process is not the command's
    prefix = tmp_path / "fresh"
    prefix.mkdir()
    entry = subprocess.run(_entry_command(["preflight"], prefix), cwd=REPOSITORY, env=_entry_environment(prefix), capture_output=True, text=True, check=False)
    assert entry.returncode == 0 and not any(prefix.iterdir()), entry.stdout + entry.stderr
    (prefix / "planted.pyc").write_bytes(b"")
    planted = subprocess.run(_entry_command(["preflight"], prefix), cwd=REPOSITORY, env=_entry_environment(prefix), capture_output=True, text=True, check=False)
    assert planted.returncode == 2 and "the fresh bytecode cache is not an empty directory" in planted.stdout
    (prefix / "planted.pyc").unlink()
    for flag in ("-I", "-S"):
        other = subprocess.run(_entry_command(["preflight"], prefix, drop=(flag,)), cwd=REPOSITORY, env=_entry_environment(prefix), capture_output=True, text=True, check=False)
        assert other.returncode == 2 and f"start the runner with {rn.LAUNCHER}" in other.stdout, flag


_HOOK = """
import importlib.machinery, sys
from pathlib import Path
Path({marker!r}).write_text("ran")


class Transforming(importlib.machinery.SourceFileLoader):
    def source_to_code(self, data, path, *, _optimize=-1):
        data = data + b"\\ndef open_interest_intensity(*args, **kwargs):\\n    return 136\\n"
        return super().source_to_code(data, path)


class Finder:
    @classmethod
    def find_spec(cls, name, path=None, target=None):
        if name != "btc_predictor.features.positioning":
            return None
        spec = importlib.machinery.PathFinder.find_spec(name, path, target)
        spec.loader = Transforming(name, spec.origin)
        return spec


sys.meta_path.insert(0, Finder)
"""


def test_an_inherited_startup_hook_never_runs_in_the_command(monkeypatch, tmp_path):
    # review RR3: a sitecustomize on PYTHONPATH installed a transforming source loader and the check passed
    import os
    import sys

    hooks = tmp_path / "hooks"
    hooks.mkdir()
    marker = tmp_path / "hook-ran"
    (hooks / "sitecustomize.py").write_text(_HOOK.format(marker=str(marker)))
    probe = (
        "import sys; from pathlib import Path; from btc_predictor.research_backtest import runner as rn; "
        "from btc_predictor.features import positioning; "
        "rn.frozen_code_paths(Path('.').resolve(), list(sys.modules.items()))"
    )
    # in an ordinary process the hook runs, and the loader check refuses its subclass
    hooked = subprocess.run(
        [sys.executable, "-B", "-c", probe], cwd=REPOSITORY, env={**os.environ, "PYTHONPATH": str(hooks)}, capture_output=True, text=True, check=False
    )
    assert marker.exists() and hooked.returncode != 0 and "FROZEN_CODE_REFUSED" in hooked.stderr
    marker.unlink()
    # review N2: no ordinary interpreter runs first, so the launcher's process never runs it, inherited or given
    hooked_environment = {"PYTHONPATH": str(hooks), "PYTHONSTARTUP": str(hooks / "sitecustomize.py")}
    launched = _launched(["preflight"], tmp_path, hooked_environment)
    assert launched.returncode == 0 and not marker.exists(), launched.stdout + launched.stderr
    prefix = tmp_path / "fresh"
    prefix.mkdir()
    given = subprocess.run(
        _entry_command(["preflight"], prefix), cwd=REPOSITORY, env=_entry_environment(prefix, **hooked_environment), capture_output=True, text=True, check=False
    )
    # given them directly, the interpreter still never runs the hook; review Q1's check then refuses the variables
    assert given.returncode == 2 and "PYTHONPATH is set" in given.stdout and not marker.exists(), given.stdout + given.stderr


def test_the_launchers_shell_runs_nothing_its_caller_names(tmp_path):
    import os

    # review T1: an ordinary bash runs a BASH_ENV file and imports exported functions before the script's first line
    marker = tmp_path / "shell-ran"
    startup = tmp_path / "bash_env.sh"
    startup.write_text(f"echo bash_env >> {marker}\n")
    planted = tmp_path / "planted"
    planted.mkdir()
    for name in ("env", "mktemp", "rm", "dirname"):
        (planted / name).write_text(f'#!/bin/sh\necho {name} >> {marker}\nexec /usr/bin/{name} "$@"\n')
        (planted / name).chmod(0o755)
    named = {
        "BASH_ENV": str(startup),
        "ENV": str(startup),
        "BASH_FUNC_env%%": f"() {{  echo function >> {marker}; }}",
        "BASH_FUNC_command%%": f"() {{  echo function >> {marker}; }}",
        "SHELLOPTS": "xtrace",
        "PATH": f"{planted}:{os.environ['PATH']}",
    }
    # each would act in an ordinary bash: the startup file, the functions, the planted helpers and the inherited option
    ordinary = subprocess.run(["/bin/bash", "-c", "env true; command true; mktemp -u >/dev/null"], env=named, capture_output=True, text=True, check=False)
    assert marker.read_text().split() == ["bash_env", "function", "function", "mktemp"] and "+ " in ordinary.stderr
    marker.unlink()
    # the launcher, started by its first line: none of them acts, and its process is the one an empty environment gives
    clean = json.loads(_launched(["preflight"], tmp_path).stdout)
    launched = _launched(["preflight"], tmp_path, named)
    assert launched.returncode == 0 and not marker.exists() and launched.stderr == "", launched.stdout + launched.stderr
    report = json.loads(launched.stdout)
    assert report["path"] == clean["path"] and report["modules_from_source"] == clean["modules_from_source"]
    assert set(report["environment"]) - {"LC_CTYPE"} == _LAUNCHED_ENVIRONMENT
    assert not any((tmp_path / "launcher-tmp").iterdir())
    # started unprivileged, the launcher refuses before anything else
    assert LAUNCHER.read_text().splitlines()[0] == "#!/bin/bash -p"
    for shell in (["/bin/bash"], ["/bin/sh"]):
        other = _launched(["preflight"], tmp_path, shell=shell)
        assert other.returncode == 2 and other.stdout == "" and "so bash runs privileged (-p) from its first line" in other.stderr, shell
    assert not any((tmp_path / "launcher-tmp").iterdir())


def test_the_commit_checks_run_the_systems_git_with_no_caller_configuration(tmp_path):
    import os

    # review Q1: the interpreter inherited the caller's PATH and HOME, so the caller chose the git that checks the
    # commit and compares the frozen source, and that git read the caller's global configuration
    marker = tmp_path / "git-ran"
    planted = tmp_path / "planted"
    planted.mkdir()
    (planted / "git").write_text(f'#!/bin/sh\necho git >> {marker}\nexec /usr/bin/git "$@"\n')
    (planted / "git").chmod(0o755)
    monitor = tmp_path / "fsmonitor"
    monitor.write_text(f"#!/bin/sh\necho fsmonitor >> {marker}\nexit 1\n")
    monitor.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitconfig").write_text(f"[core]\n\tfsmonitor = {monitor}\n")
    named = {"PATH": f"{planted}:{os.environ['PATH']}", "HOME": str(home)}
    # each acts in an ordinary process: the planted git runs, and the real one runs the configured hook
    status = ["git", "-C", str(REPOSITORY), "status", "--porcelain", "--untracked-files=no"]
    subprocess.run(status, env=named, capture_output=True, check=True)
    assert set(marker.read_text().split()) == {"git", "fsmonitor"}
    marker.unlink()
    # the launcher's run: neither acts, and the run goes exactly as far as a clean launch, whatever stops it
    store = tmp_path / "store"
    store.mkdir()
    command = ["run", "--store", str(store), "--workers", "1"]
    clean = _launched(command, tmp_path)
    launched = _launched(command, tmp_path, named)
    assert not marker.exists(), launched.stdout + launched.stderr
    assert (launched.returncode, launched.stdout, launched.stderr) == (clean.returncode, clean.stdout, clean.stderr)
    assert "the environment is not the launcher's" not in clean.stdout + clean.stderr  # it reaches the commit checks
    assert not any(store.iterdir()) and not any((tmp_path / "launcher-tmp").iterdir())
    # started without the launcher's environment, the run refuses before any git runs
    prefix = tmp_path / "fresh"
    prefix.mkdir()
    for environment in ({**named, rn.FRESH_BYTECODE_ENV: str(prefix)}, _entry_environment(prefix, HOME=str(home)), {**_entry_environment(prefix), "PATH": named["PATH"]}):
        entry = subprocess.run(_entry_command(command, prefix), cwd=REPOSITORY, env=environment, capture_output=True, text=True, check=False)
        assert entry.returncode == 2 and "refused: FROZEN_CODE_REFUSED: the environment is not the launcher's" in entry.stdout, entry.stdout + entry.stderr
        assert not marker.exists() and not any(prefix.iterdir())


def test_the_launch_environment_check_accepts_only_the_launchers(monkeypatch, tmp_path):
    import os
    import sys

    # review Q1: the fixed standard path, both git variables, and nothing else but the locale and TMPDIR
    launched = _entry_environment(tmp_path)
    assert rn.launch_environment_refusals(launched) == []
    assert rn.launch_environment_refusals({**launched, "LANG": "C.UTF-8", "LC_ALL": "C", "LC_CTYPE": "C.UTF-8", "TMPDIR": "/tmp"}) == []
    assert os.confstr("CS_PATH") == subprocess.run(["/bin/bash", "-c", "command -p getconf PATH"], env={}, capture_output=True, text=True, check=True).stdout.strip()
    without = {name: {key: value for key, value in launched.items() if key != name} for name in ("PATH", *rn.LAUNCH_GIT_ENVIRONMENT)}
    changes = {
        "PATH elsewhere": {**launched, "PATH": f"{tmp_path}:{launched['PATH']}"},
        "no PATH": without["PATH"],
        "system configuration": without["GIT_CONFIG_NOSYSTEM"],
        "system configuration read": {**launched, "GIT_CONFIG_NOSYSTEM": "0"},
        "global configuration": without["GIT_CONFIG_GLOBAL"],
        "global configuration named": {**launched, "GIT_CONFIG_GLOBAL": str(tmp_path / ".gitconfig")},
        "HOME": {**launched, "HOME": str(tmp_path)},
        "XDG_CONFIG_HOME": {**launched, "XDG_CONFIG_HOME": str(tmp_path)},
        "GIT_DIR": {**launched, "GIT_DIR": str(tmp_path)},
        "GIT_CONFIG_COUNT": {**launched, "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.fsmonitor", "GIT_CONFIG_VALUE_0": "true"},
        "LD_PRELOAD": {**launched, "LD_PRELOAD": str(tmp_path / "x.so")},
    }
    for name, environment in changes.items():
        assert rn.launch_environment_refusals(environment), name
    # this test process is not the launcher's, and the fresh-process check names its environment
    assert rn.launch_environment_refusals()
    monkeypatch.setattr(rn, "fresh_bytecode_process", lambda: True)
    monkeypatch.setattr(rn, "startup_refusals", lambda: [])
    monkeypatch.setattr(sys, "pycache_prefix", str(tmp_path))
    with pytest.raises(rn.RunnerRefused, match="the environment is not the launcher's"):
        rn.require_fresh_bytecode()
    monkeypatch.setattr(os, "environ", launched)
    assert rn.require_fresh_bytecode() == str(tmp_path)


def test_the_startup_check_needs_the_interpreters_own_import_system(monkeypatch, tmp_path):
    import builtins
    import importlib.machinery as machinery
    import sys
    import zipimport

    file_finder = next(hook for hook in sys.path_hooks if getattr(hook, "__qualname__", "").startswith("FileFinder.path_hook"))
    clean = {
        "flags": SimpleNamespace(isolated=1, no_site=1, ignore_environment=1, safe_path=True),
        "modules": {},
        "meta_path": [machinery.BuiltinImporter, machinery.FrozenImporter, machinery.PathFinder],
        "path_hooks": [zipimport.zipimporter, file_finder],
        "loader": machinery.SourceFileLoader,
        "builtins_module": builtins,
    }
    assert rn.startup_refusals(**clean) == []

    class Patched(machinery.SourceFileLoader):
        def get_code(self, fullname):
            return super().get_code(fullname)

    changes = [
        ("flags", SimpleNamespace(isolated=1, no_site=0, ignore_environment=1, safe_path=True)),
        ("modules", {"sitecustomize": object()}),
        ("meta_path", [object, *clean["meta_path"]]),
        ("path_hooks", [zipimport.zipimporter, file_finder, lambda path: None]),
        ("path_hooks", [lambda path: None, file_finder]),
        ("loader", Patched),
        ("builtins_module", SimpleNamespace(compile=lambda *args: None, exec=builtins.exec)),
    ]
    for name, value in changes:
        assert rn.startup_refusals(**{**clean, name: value}), name
    # this test process (pytest's own import hook, no isolation) is not such a process, even with a fresh cache
    assert rn.startup_refusals()
    monkeypatch.setattr(rn, "fresh_bytecode_process", lambda: True)
    monkeypatch.setattr(sys, "pycache_prefix", str(tmp_path))
    with pytest.raises(rn.RunnerRefused, match="import system"):
        rn.require_fresh_bytecode()


def test_main_refuses_outside_the_launchers_process():
    import sys

    # review N2: the parent the command ran itself again from had already run its startup; now nothing runs again
    lines = []
    assert rn.main(["run", "--workers", "3"], out=lines.append) == 2
    assert len(lines) == 1 and lines[0].startswith(f"refused: FROZEN_CODE_REFUSED: start the runner with {rn.LAUNCHER}")
    module = subprocess.run([sys.executable, "-m", "btc_predictor.research_backtest.runner", "--help"], cwd=REPOSITORY, capture_output=True, text=True, check=False)
    assert module.returncode == 2 and str(rn.LAUNCHER) in module.stdout and "usage" not in module.stdout
    assert not hasattr(rn, "run_with_fresh_bytecode") and not hasattr(rn, "fresh_python_command")


def test_stale_bytecode_runs_in_a_normal_import_but_never_in_the_fresh_process(tmp_path):
    import os
    import py_compile
    import sys

    # review F5's probe: a same-length change compiled, then the source restored with its size and time
    package = tmp_path / "package"
    package.mkdir()
    source = package / "frozen_value.py"
    source.write_text("VALUE = 29\n")
    os.utime(source, (1_700_000_000, 1_700_000_000))
    py_compile.compile(str(source), doraise=True)
    source.write_text("VALUE = 28\n")
    os.utime(source, (1_700_000_000, 1_700_000_000))
    probe = ["-c", "import frozen_value; print(frozen_value.VALUE)"]
    normal = subprocess.run([sys.executable, *probe], cwd=package, capture_output=True, text=True, check=True)
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    isolated = subprocess.run([sys.executable, "-B", "-X", f"pycache_prefix={fresh}", *probe], cwd=package, capture_output=True, text=True, check=True)
    assert normal.stdout.strip() == "29" and isolated.stdout.strip() == "28" and not any(fresh.iterdir())


def test_a_module_loaded_during_the_run_is_checked_where_it_loads(monkeypatch, preregistration, tmp_path):
    import sys

    loaded = {name for name in sys.modules if rn._repository_module(name)}
    monkeypatch.setattr(rn, "_STATE", {"frozen": (REPOSITORY, preregistration["code_commit"]), "checked_modules": set(loaded)})
    # review RR3: an import system changed during the run refuses (pytest's own hook is one)
    with pytest.raises(rn.RunnerRefused, match="FROZEN_CODE_REFUSED"):
        rn.verify_loaded_code()
    monkeypatch.setattr(rn, "startup_refusals", lambda: [])
    rn.verify_loaded_code()
    # a real owner seen for the first time is compared with the frozen commit and then remembered
    rn._STATE["checked_modules"].discard("btc_predictor.features.positioning")
    rn.verify_loaded_code()
    assert "btc_predictor.features.positioning" in rn._STATE["checked_modules"]
    elsewhere = tmp_path / "late.py"
    elsewhere.write_text("VALUE = 1\n")
    monkeypatch.setitem(sys.modules, "btc_predictor.late_module", _module("btc_predictor.late_module", elsewhere))
    with pytest.raises(rn.RunnerRefused, match="FROZEN_CODE_REFUSED"):
        rn.verify_loaded_code()
    with pytest.raises(rn.RunnerRefused, match="FROZEN_CODE_REFUSED"):
        rn._verified(lambda argument: argument)(1)


# --- windows, folds and runs ----------------------------------------------------------------------------


def test_a_headline_run_composes_exactly_its_window(headline):
    rows = headline.record["entry_ledger"]
    assert rows[0]["decision_at"] == START.isoformat() and rows[-1]["decision_at"] == LAST.isoformat()
    assert len(rows) == (LAST - START) // DAY + 1
    assert all(rn._bar_available_at(bar) < LAST + DAY for bar in headline.result.input_bars)
    assert headline.record["unaccounted"] == []
    assert headline.record["memory"]["matches_history"] and headline.record["memory"]["compared_rows"] == len(rows)
    assert headline.record["trade_entries"] == {"0": "2024-03-31T00:00:00+00:00"}
    assert headline.record["engine_events"]["INTENT:ARM_ENTRY:QUEUED"] == 1


def test_ruling_4_folds_are_4368_hourly_bars_from_the_evaluation_start(walk_forward):
    assert rn.FOLD_BARS == 4368
    folds = walk_forward.record["folds"]
    assert [fold["bars"] for fold in folds] == [SYNTHETIC_FOLD_BARS] * 3
    assert folds[0]["first_decision"] == START.isoformat()
    assert [fold["decisions"] for fold in folds] == [7, 7, 7]
    assert walk_forward.record["plan"]["embargo_periods"] == 0 and walk_forward.record["plan"]["scheme"] == "expanding"
    assert "regime_breakdown" in walk_forward.record and "validation" not in walk_forward.record["regime_breakdown"]


def test_a_fold_shifted_by_omitted_hours_starts_from_the_history_before_its_first_decision(preregistration):
    # review F1: two omitted hours shift every later fold to start at 02:00 (ruling 4's Bitfinex case)
    gapped = management_market(end=utc(2024, 4, 20), missing_hours=(utc(2024, 3, 26, 10), utc(2024, 3, 26, 11))).build()
    history = {"BITSTAMP": rn.continuous_history(gapped, CONFIG, LAST, SCHEDULE)}
    context = rn.RunContext(
        inputs={"BITSTAMP": gapped},
        registry=_registry(preregistration),
        evaluation={"BITSTAMP": (START, LAST)},
        fold_bars=SYNTHETIC_FOLD_BARS,
        history=history,
        schedule=SCHEDULE,
    )
    outcome = rn.execute_run(rn.RunSpec(rn.WALK_FORWARD, "BITSTAMP", rn.CHAMPION, "base"), context)
    folds = outcome.record["folds"]
    window = rn.bars_before(rn.venue_bars(gapped), LAST + DAY)
    starts = [rn._bar_available_at(window[w.test_start_index]) for w in rn.walk_forward_windows([bar.timestamp for bar in window], plan=rn.fold_plan_bars(CONFIG, window, START, SYNTHETIC_FOLD_BARS))]
    assert [start.hour for start in starts] == [0, 2, 2]
    assert [fold["first_decision"] for fold in folds] == [day.isoformat() for day in (START, utc(2024, 4, 2), utc(2024, 4, 9))]
    assert [fold["decisions"] for fold in folds] == [8, 7, 7]
    assert [(fold["omitted_hours_before_start"], fold["omitted_hours_before_end"]) for fold in folds] == [(0, 2), (2, 2), (2, 2)]
    for fold, ledger, strategy in zip(folds, outcome.record["entry_ledgers"], outcome.composers, strict=True):
        first = rn.datetime.fromisoformat(fold["first_decision"])
        assert ledger[0]["decision_at"] == fold["first_decision"]
        seeded = strategy.entry.ledger[: strategy.entry.seeded]
        assert seeded == tuple(row for row in history["BITSTAMP"] if row.decision_at < first) and seeded[-1].decision_at == first - DAY
    assert outcome.record["memory"]["matches_history"] and outcome.record["unaccounted"] == []
    assert rn.first_decision_at(utc(2024, 4, 1, 2)) == utc(2024, 4, 2) and rn.first_decision_at(START) == START


def test_the_ruling_4_check_compares_the_preregistered_fold_dates(preregistration):
    frozen = preregistration["venues"]["BITSTAMP"]["walk_forward"]["folds"]

    def folds(hours):
        # each fold: its preregistered boundaries moved by the hours omitted before them
        out = []
        for item, (before_start, before_end) in zip(frozen, hours, strict=True):
            first = rn.first_decision_at(rn.datetime.fromisoformat(item["test_start"]) + timedelta(hours=before_start))
            last = rn.first_decision_at(rn.datetime.fromisoformat(item["test_end"]) + DAY + timedelta(hours=before_end)) - DAY
            out.append(
                {
                    "fold_number": item["fold_number"],
                    "first_decision": first.isoformat(),
                    "last_decision": last.isoformat(),
                    "decisions": (last - first) // DAY + 1,
                    "omitted_hours_before_start": before_start,
                    "omitted_hours_before_end": before_end,
                }
            )
        return out

    same = rn_report_check("BITSTAMP", folds([(0, 0)] * 3), preregistration["venues"]["BITSTAMP"])
    assert same["equal"] and same["consistent"]
    # ruling 4's Bitfinex case: two hours omitted inside fold 1
    shifted = rn_report_check("BITFINEX", folds([(0, 2), (2, 2), (2, 2)]), preregistration["venues"]["BITSTAMP"])
    assert not shifted["equal"] and shifted["consistent"] and shifted["decisions_per_fold"] == [183, 182, 182]
    assert shifted["run"][0]["last_decision"] == "2024-09-08T00:00:00+00:00" and shifted["run"][1]["first_decision"] == "2024-09-09T00:00:00+00:00"
    # a shift no omitted hour explains, or a missing fold, must fail
    moved = folds([(0, 0)] * 3)
    moved[1]["first_decision"] = "2024-09-09T00:00:00+00:00"
    assert not rn_report_check("BITSTAMP", moved, preregistration["venues"]["BITSTAMP"])["consistent"]
    assert not rn_report_check("BITSTAMP", folds([(0, 0)] * 3)[:2], preregistration["venues"]["BITSTAMP"])["consistent"]


def rn_report_check(venue, folds, frozen):
    return rr.ruling4_check(venue, folds, frozen)


def test_a_golden_window_holds_each_period_days_close():
    first, last = rn.golden_window({"period": {"start": "2023-07-20", "end": "2023-08-25"}})
    assert (first, last) == (utc(2023, 7, 21), utc(2023, 8, 26))


def test_a_history_that_stops_short_of_a_window_refuses(context):
    short = replace(context, history={"BITSTAMP": tuple(row for row in context.history["BITSTAMP"] if row.decision_at < START - 2 * DAY)})
    with pytest.raises(rn.RunnerRefused, match="HISTORY_REFUSED"):
        short.seed("BITSTAMP", START)


def test_an_empty_history_refuses_every_seed(context):
    # review F3: an empty history once seeded nothing and matched itself
    for history in ({}, {"BITSTAMP": ()}):
        with pytest.raises(rn.RunnerRefused, match="HISTORY_REFUSED"):
            replace(context, history=history).seed("BITSTAMP", START)
    assert context.seed("BITSTAMP", SCHEDULE[0]) == ()
    with pytest.raises(rn.RunnerRefused, match="HISTORY_REFUSED"):
        replace(context, history={"BITSTAMP": context.history["BITSTAMP"][1:]}).seed("BITSTAMP", SCHEDULE[0])


def test_the_memory_check_needs_every_composed_row_compared(context, headline):
    rows = context.history["BITSTAMP"]
    assert rn.memory_check(context, "BITSTAMP", headline.composers)["matches_history"]
    short = replace(context, history={"BITSTAMP": tuple(row for row in rows if row.decision_at != START + 3 * DAY)})
    check = rn.memory_check(short, "BITSTAMP", headline.composers)
    assert not check["matches_history"] and check["mismatches"] == []
    assert not rn.memory_check(replace(context, history={}), "BITSTAMP", headline.composers)["matches_history"]


def test_a_checkpoint_is_read_back_only_under_its_own_binding(tmp_path, context, headline):
    spec = rn.RunSpec(rn.HEADLINE, "BITSTAMP", rn.CHAMPION, "base")
    binding = rn.run_binding(spec, context)
    stored = json.loads(canonical_json_bytes(headline.record))
    assert stored["binding"] == json.loads(canonical_json_bytes(binding))
    assert rn.read_run(tmp_path, spec, context) is None
    rn.write_run(tmp_path, headline)
    assert rn.read_run(tmp_path, spec, context) == stored
    for changed in (
        {**binding, "context": {"other_dataset": True}},
        {**binding, "window": [START.isoformat(), (LAST - DAY).isoformat()]},
        {**binding, "configuration_sha256": "0" * 64},
        {**binding, "history_sha256": "0" * 64},
    ):
        with pytest.raises(rn.RunnerRefused, match="CHECKPOINT_REFUSED"):
            rn.read_run(tmp_path, spec, context, binding=changed)
    path = rn.run_file(tmp_path, spec)
    for record in (
        {**stored, "metrics": {"invented": 1}, "binding": {"FOREIGN": True}},
        {key: value for key, value in stored.items() if key != "binding"},
        {key: value for key, value in stored.items() if key != "memory"},
        {**stored, "run_id": "HEADLINE:COINBASE:champion:base"},
    ):
        path.write_bytes(gzip.compress(canonical_json_bytes(record)))
        with pytest.raises(rn.RunnerRefused, match="CHECKPOINT_REFUSED"):
            rn.read_run(tmp_path, spec, context)
    path.write_bytes(b"not a record")
    with pytest.raises(rn.RunnerRefused, match="CHECKPOINT_REFUSED"):
        rn.read_run(tmp_path, spec, context)


def test_a_checkpoint_is_read_only_if_its_snapshot_gives_it(tmp_path, context, headline, walk_forward):
    # review RR2: a correctly bound record with emptied ledgers and an invented rate was read and published
    spec = rn.RunSpec(rn.HEADLINE, "BITSTAMP", rn.CHAMPION, "base")
    rn.write_run(tmp_path, headline)
    stored = rn.read_run(tmp_path, spec, context)
    path = rn.run_file(tmp_path, spec)
    assert rn.run_snapshot_file(tmp_path, spec).exists()

    def named(record, run=spec):
        # each record names its snapshot file's digest (review N1), so the checks after it are reached
        return {**record, rn.SNAPSHOT_DIGEST: hashlib.sha256(rn.run_snapshot_file(tmp_path, run).read_bytes()).hexdigest()}

    def refused(record, match="CHECKPOINT_REFUSED"):
        path.write_bytes(gzip.compress(canonical_json_bytes(named(record))))
        with pytest.raises(rn.RunnerRefused, match=match):
            rn.read_run(tmp_path, spec, context)

    invented = copy.deepcopy(stored)
    invented["entry_ledger"], invented["management_ledger"] = [], []
    invented["metrics"]["win_rate"] = {**invented["metrics"]["win_rate"], "status": "AVAILABLE", "value": "0.987650000000"}
    assert invented["metrics"]["win_rate"]["closed_trades"] == stored["metrics"]["win_rate"]["closed_trades"]
    for change in (
        lambda r: r.update(entry_ledger=[]),
        lambda r: r.update(management_ledger=r["management_ledger"][:-1]),
        lambda r: r["metrics"]["win_rate"].update(value="0.987650000000"),
        lambda r: r.update(trade_entries={}),
        lambda r: r["engine_events"].update({"INTENT:ARM_ENTRY:QUEUED": 2}),
        lambda r: r.update(unaccounted=["entry:x:CODE"]),
        lambda r: r["memory"].update(compared_rows=1),
        lambda r: r["result"].update(ending_nav="1"),
        lambda r: r["entry_ledger"][3].update(outcome="ARMED"),
    ):
        record = copy.deepcopy(stored)
        change(record)
        refused(record)
    refused(invented)

    # the snapshot must be there, this run's, under this binding
    snapshot_path = rn.run_snapshot_file(tmp_path, spec)
    good = pickle.loads(gzip.decompress(snapshot_path.read_bytes()))
    for data in (None, {**good, "run_id": "HEADLINE:COINBASE:champion:base"}, {**good, "binding": {"foreign": True}}, {**good, "snapshot": None}):
        snapshot_path.write_bytes(gzip.compress(pickle.dumps(data)))
        path.write_bytes(gzip.compress(canonical_json_bytes(named(stored))))
        with pytest.raises(rn.RunnerRefused, match="CHECKPOINT_REFUSED"):
            rn.read_run(tmp_path, spec, context)
    snapshot_path.unlink()
    with pytest.raises(rn.RunnerRefused, match="CHECKPOINT_REFUSED"):
        rn.read_run(tmp_path, spec, context)

    # a snapshot that is not a complete run refuses, even beside the record it gives
    from btc_predictor.research_backtest import management_composer as mc

    def incomplete(run, variant, fallback):
        assert rn.snapshot_refusals(run, context, variant)
        try:
            consistent = rn.run_record(run, context, variant)
        except Exception:
            consistent = fallback
        rn.run_snapshot_file(tmp_path, run).write_bytes(gzip.compress(pickle.dumps({**good, "run_id": run.run_id, "binding": fallback["binding"], "snapshot": variant})))
        rn.run_file(tmp_path, run).write_bytes(gzip.compress(canonical_json_bytes(named(consistent, run))))
        with pytest.raises(rn.RunnerRefused, match="CHECKPOINT_REFUSED"):
            rn.read_run(tmp_path, run, context)

    snapshot, (composer,) = good["snapshot"], good["snapshot"].composers
    arm = next(index for index, row in enumerate(composer.entry_rows) if row.intent is not None)
    managed = composer.management_rows[0].decision_at
    # one bar changed mid-window: the span, and so the ledgers' coverage, unchanged
    altered = list(rn.run_bars(spec, context))
    altered[10] = replace(altered[10], volume=altered[10].volume + 1)
    shortened = copy.copy(snapshot.result)
    object.__setattr__(shortened, "input_bars", tuple(altered))
    cases = {
        "entry ledger": replace(composer, entry_rows=composer.entry_rows[:-1]),
        "entry ledger gap": replace(composer, entry_rows=composer.entry_rows[:4] + composer.entry_rows[5:]),
        "management ledger": replace(composer, management_rows=composer.management_rows[1:]),
        "position": replace(composer, entry_rows=tuple(replace(row, position_open=False) if row.decision_at == managed else row for row in composer.entry_rows)),
        "intents": replace(composer, entry_rows=tuple(replace(row, intent=None) if index == arm else row for index, row in enumerate(composer.entry_rows))),
        "follow-ups": replace(composer, followups=(*composer.followups, mc.AddFollowUp(managed, managed, "INVENTED", (), {"source_id": "invented"}))),
        "seeding": replace(composer, first=START + DAY),
    }
    variants = {name: replace(snapshot, composers=(item,)) for name, item in cases.items()}
    variants["engine bars"] = replace(snapshot, result=shortened)
    variants["shape"] = replace(snapshot, validation=walk_forward.snapshot.validation)
    variants["contexts"] = replace(snapshot, trade_contexts=("invented",))
    for name, variant in variants.items():
        incomplete(spec, variant, stored)

    # every synthetic run kind reads back; a fold's snapshot is checked fold by fold
    folded = rn.RunSpec(rn.WALK_FORWARD, "BITSTAMP", rn.CHAMPION, "base")
    rn.write_run(tmp_path, walk_forward)
    folded_record = rn.read_run(tmp_path, folded, context)
    assert folded_record == json.loads(canonical_json_bytes(walk_forward.record))
    assert rn.snapshot_refusals(folded, context, walk_forward.snapshot) == []
    composers = walk_forward.snapshot.composers
    for variant in (
        replace(walk_forward.snapshot, composers=composers[:-1]),
        replace(walk_forward.snapshot, composers=(composers[0], replace(composers[1], entry_rows=composers[1].entry_rows[1:]), composers[2])),
        replace(walk_forward.snapshot, composers=(composers[1], composers[0], composers[2])),
        replace(walk_forward.snapshot, result=snapshot.result),
    ):
        incomplete(folded, variant, folded_record)


def test_store_files_are_read_with_only_the_classes_they_hold(tmp_path, context, headline, monkeypatch):
    # review N1: the snapshot was unpickled before anything checked it, and a pickle builds whatever it names
    import collections
    import dataclasses
    import importlib

    spec = rn.RunSpec(rn.HEADLINE, "BITSTAMP", rn.CHAMPION, "base")
    hooks = {"__reduce__", "__reduce_ex__", "__setstate__", "__getstate__", "__getnewargs__", "__getnewargs_ex__", "__new__", "__slots__"}
    for module, name in rs.STORE_CLASSES:
        cls = getattr(importlib.import_module(module), name)
        if module not in ("datetime", "decimal"):
            assert dataclasses.is_dataclass(cls) and cls.__dataclass_params__.frozen and not hooks & set(vars(cls)), name
    # the store's objects come back whole; any other name is refused on write and on read, and named
    loaded = rs.load_store_pickle(rs.dump_store_pickle(headline.snapshot))
    assert canonical_json_bytes(rn.run_record(spec, context, loaded)) == canonical_json_bytes(headline.record)
    for other in (Path("/elsewhere"), len, collections.Counter(), spec, [Decimal("1"), json.dumps]):
        with pytest.raises(pickle.UnpicklingError, match="is not a class the store files hold"):
            rs.load_store_pickle(pickle.dumps(other))
        with pytest.raises(pickle.UnpicklingError, match="is not a class the store files hold"):
            rs.dump_store_pickle(other)

    # each of the four readers refuses a file naming another class, with its own refusal
    rn.write_run(tmp_path, headline)
    stored = rn.read_run(tmp_path, spec, context)
    snapshot_path = rn.run_snapshot_file(tmp_path, spec)
    good_bytes = snapshot_path.read_bytes()
    good = pickle.loads(gzip.decompress(good_bytes))
    raw = gzip.compress(pickle.dumps({**good, "snapshot": replace(good["snapshot"], trade_contexts=(spec,))}))
    snapshot_path.write_bytes(raw)
    rn.run_file(tmp_path, spec).write_bytes(gzip.compress(canonical_json_bytes({**stored, rn.SNAPSHOT_DIGEST: hashlib.sha256(raw).hexdigest()})))
    workspace = rn.Workspace(tmp_path / "work")
    rn._write_whole(rn.history_file(workspace, "BITSTAMP"), pickle.dumps({"binding": rn.history_binding(context, "BITSTAMP", LAST), "rows": (spec,)}))
    rn._write_whole(rn.audit_state_file(workspace, "BITSTAMP"), pickle.dumps({"binding": {}, "state": spec}))
    for code, read in (
        ("CHECKPOINT_REFUSED", lambda: rn.read_run(tmp_path, spec, context)),
        ("HISTORY_REFUSED", lambda: rn.read_history(workspace, "BITSTAMP", context, LAST)),
        ("AUDIT_REFUSED", lambda: rn.load_audit_state(workspace, "BITSTAMP", {})),
    ):
        with pytest.raises(rn.RunnerRefused, match="RunSpec is not a class the store files hold") as refusal:
            read()
        assert refusal.value.code == code
    store = rs.SharedResultStore(tmp_path / "shared")
    key = "ab" * 32
    store._path(key).parent.mkdir(parents=True)
    store._path(key).write_bytes(pickle.dumps((rs._FILE_TAG, key, "funding_health", spec)))
    with pytest.raises(rs.SharedPositioningError, match="RunSpec is not a class the store files hold"):
        store.get(key, "funding_health")
    with pytest.raises(pickle.UnpicklingError):
        store.put("cd" * 32, "funding_health", spec)
    assert not store._path("cd" * 32).exists()

    # the snapshot is read only if it is the file its record names: other bytes never reach the loader
    snapshot_path.write_bytes(good_bytes)
    rn.run_file(tmp_path, spec).write_bytes(gzip.compress(canonical_json_bytes({**stored, rn.SNAPSHOT_DIGEST: hashlib.sha256(good_bytes).hexdigest()})))
    loads = []
    monkeypatch.setattr(rn, "load_store_pickle", lambda data: loads.append(data) or rs.load_store_pickle(data))
    assert rn.read_run(tmp_path, spec, context) == stored and len(loads) == 1
    loads.clear()
    for replaced in (gzip.compress(pickle.dumps({**good, "binding": {"foreign": True}})), good_bytes + b"\0", b""):
        snapshot_path.write_bytes(replaced)
        with pytest.raises(rn.RunnerRefused, match="is not the snapshot"):
            rn.read_run(tmp_path, spec, context)
    snapshot_path.write_bytes(good_bytes)
    for record in ({**stored, rn.SNAPSHOT_DIGEST: "0" * 64}, {**stored, rn.SNAPSHOT_DIGEST: None}, stored):
        rn.run_file(tmp_path, spec).write_bytes(gzip.compress(canonical_json_bytes(record)))
        with pytest.raises(rn.RunnerRefused, match="CHECKPOINT_REFUSED"):
            rn.read_run(tmp_path, spec, context)
    assert loads == []


@contextlib.contextmanager
def _trail_and_add(run_context, share, *, dropped):
    """RBT-005's trail-and-add instant through the runner; dropped, the risk at the stop exceeds the ceiling at the callback."""

    from btc_predictor.research_backtest import management_composer as mc
    from btc_predictor.tests.rbt005_management_fixtures import TRAIL_AT, Interventions, add_score_lifted, higher_low_at

    inputs = run_context.inputs["BITSTAMP"]
    with pytest.MonkeyPatch.context() as patch:
        changes = Interventions(patch)
        higher_low_at(changes, inputs, {TRAIL_AT})
        add_score_lifted(changes, {TRAIL_AT})
        if dropped:
            changes.result(mc, "calculate_risk_at_stop", {TRAIL_AT + timedelta(hours=1)}, within_maximum=False)
        call = mc.ManagementComposer.__call__

        def serving(self, engine_context):
            changes.instant = engine_context.as_of
            return call(self, engine_context)

        patch.setattr(mc.ManagementComposer, "__call__", serving)
        with share():
            yield


def test_every_pending_add_has_exactly_its_one_resolution(tmp_path, context, share):
    # review N3: a dropped ADD follow-up returns no intent and reaches the record only through its causes,
    # so removing it from a snapshot left the rebuilt record unchanged and the checkpoint was read
    from btc_predictor.research_backtest import management_composer as mc
    from btc_predictor.tests.rbt005_management_fixtures import TRAIL_AT

    hour = timedelta(hours=1)
    spec = rn.RunSpec(rn.HEADLINE, "BITSTAMP", rn.CHAMPION, "base")

    def trail_and_add(run_context, *, dropped):
        with _trail_and_add(run_context, share, dropped=dropped):
            return rn.execute_run(spec, run_context, record_management=True)

    emitted, dropped = trail_and_add(context, dropped=False), trail_and_add(context, dropped=True)
    for outcome, kind in ((emitted, mc.FOLLOWUP_ADD_EMITTED), (dropped, mc.FOLLOWUP_ADD_DROPPED)):
        ((followup,),) = [composer.followups for composer in outcome.snapshot.composers]
        assert (followup.outcome, followup.decision_at, followup.resolved_at) == (kind, TRAIL_AT, TRAIL_AT + hour)
        assert rn.snapshot_refusals(spec, context, outcome.snapshot) == []
        rn.write_run(tmp_path / kind, outcome)
        assert rn.read_run(tmp_path / kind, spec, context) == json.loads(canonical_json_bytes(outcome.record))

    def refusals(outcome, followups):
        (composer,) = outcome.snapshot.composers
        return rn.snapshot_refusals(spec, context, replace(outcome.snapshot, composers=(replace(composer, followups=followups),)))

    (followup,) = dropped.snapshot.composers[0].followups
    assert followup.reasons == (mc.DROP_RISK_EXCEEDED_AT_CALLBACK,) and followup.intent is None
    # the reviewer's case: without its dropped follow-up the snapshot still gives the same record
    gone = replace(dropped.snapshot, composers=(replace(dropped.snapshot.composers[0], followups=()),))
    assert canonical_json_bytes(rn.run_record(spec, context, gone)) == canonical_json_bytes(dropped.record)
    for name, followups in {
        "removed": (),
        "twice": (followup, followup),
        "at a later callback": (replace(followup, resolved_at=TRAIL_AT + 2 * hour),),
        "of another instant": (replace(followup, decision_at=TRAIL_AT - DAY),),
        "without its reasons": (replace(followup, reasons=()),),
        "emitted without an intent": (replace(followup, outcome=mc.FOLLOWUP_ADD_EMITTED, reasons=()),),
        "of another outcome": (replace(followup, outcome="INVENTED"),),
    }.items():
        assert refusals(dropped, followups), name
    (followup,) = emitted.snapshot.composers[0].followups
    for name, item in {
        "another action": replace(followup, intent={**followup.intent, "action": "EXIT"}),
        "with reasons": replace(followup, reasons=(mc.DROP_POSITION_CHANGED,)),
        "called dropped": replace(followup, outcome=mc.FOLLOWUP_ADD_DROPPED),
    }.items():
        assert refusals(emitted, (item,)), name

    # a run that ends at the TRAIL leaves its ADD pending, with no follow-up, and is complete
    inputs = context.inputs["BITSTAMP"]
    shortened = replace(inputs, dataset=replace(inputs.dataset, price_bars=tuple(bar for bar in inputs.dataset.price_bars if bar.ingested_at <= TRAIL_AT)))
    ending = replace(context, inputs={"BITSTAMP": shortened}, evaluation={"BITSTAMP": (START, TRAIL_AT)})
    pending = trail_and_add(ending, dropped=False)
    assert pending.composers[0]._pending is not None and pending.snapshot.composers[0].followups == ()
    assert rn.snapshot_refusals(spec, ending, pending.snapshot) == []


def test_a_resumed_run_is_accepted_only_if_running_it_again_gives_it(monkeypatch, tmp_path, context, share):
    # review T2: a dropped ADD's reason and risk re-check reach no record, so changing them in a snapshot whose
    # digest the record then named was read; a resumed run is now run again and compared (the owner's choice)
    from btc_predictor.research_backtest import management_composer as mc

    spec = rn.RunSpec(rn.HEADLINE, "BITSTAMP", rn.CHAMPION, "base")
    runs = []
    execute = rn.execute_run
    monkeypatch.setattr(rn, "execute_run", lambda *args, **kwargs: runs.append(args[0]) or execute(*args, **kwargs))
    with _trail_and_add(context, share, dropped=True):
        assert rn.checkpointed_run(tmp_path, spec, context) is False
        written = {path: path.read_bytes() for path in (rn.run_file(tmp_path, spec), rn.run_snapshot_file(tmp_path, spec))}
        assert rn.checkpointed_run(tmp_path, spec, context) is True
    # the written run was run again, found to be this run, and kept as it was written
    assert runs == [spec, spec] and {path: path.read_bytes() for path in written} == written
    record, snapshot = rn.read_checkpoint(tmp_path, spec, context)
    (composer,) = snapshot.composers
    (followup,) = composer.followups
    assert followup.outcome == mc.FOLLOWUP_ADD_DROPPED and followup.reasons == (mc.DROP_RISK_EXCEEDED_AT_CALLBACK,)
    assert followup.risk_recheck["within_maximum"] is False and followup.risk_recheck["projected_risk_fraction_nav"] is not None

    def stored(changed):
        # the snapshot changed, and the record naming its new digest, as the writer names it
        altered = replace(snapshot, composers=(replace(composer, followups=(changed,)),))
        rn.write_run(tmp_path, rn.RunOutcome(spec, record, snapshot=altered))

    for name, changed in {
        "the reviewer's closed position": replace(followup, reasons=(mc.DROP_POSITION_CLOSED,)),
        "the reviewer's invented reason": replace(followup, reasons=("INVENTED",)),
        "the reviewer's missing re-check": replace(followup, risk_recheck=None),
        "another projected risk": replace(followup, risk_recheck={**followup.risk_recheck, "projected_risk_fraction_nav": Decimal("0.5")}),
    }.items():
        stored(changed)
        # every check of the stored files alone still passes
        assert rn.read_run(tmp_path, spec, context) == record, name
        with _trail_and_add(context, share, dropped=True):
            with pytest.raises(rn.RunnerRefused, match=f"CHECKPOINT_REFUSED.*is not the run {spec.run_id} gives when run again"):
                rn.checkpointed_run(tmp_path, spec, context)
    # the record is compared too: a feature written with one more trailing zero is an equal snapshot, not the record
    row = composer.entry_rows[-1]
    key, value = next((key, value) for key, value in row.features.items() if value is not None)
    sign, digits, exponent = value.as_tuple()
    longer = Decimal((sign, (*digits, 0), exponent - 1))
    widened = replace(snapshot, composers=(replace(composer, entry_rows=(*composer.entry_rows[:-1], replace(row, features={**row.features, key: longer}))),))
    assert widened == snapshot and format(longer, "f") != format(value, "f")
    rn.write_run(tmp_path, rn.RunOutcome(spec, rn.run_record(spec, context, widened), snapshot=widened))
    assert rn.read_run(tmp_path, spec, context) not in (None, record)
    with _trail_and_add(context, share, dropped=True):
        with pytest.raises(rn.RunnerRefused, match="gives when run again"):
            rn.checkpointed_run(tmp_path, spec, context)
    # a complete run of the same binding that running it again does not give (here the ADD emitted) is refused too
    with _trail_and_add(context, share, dropped=False):
        emitted = execute(spec, context)
    assert emitted.snapshot.composers[0].followups[0].outcome == mc.FOLLOWUP_ADD_EMITTED
    rn.write_run(tmp_path, emitted)
    assert rn.read_run(tmp_path, spec, context) == json.loads(canonical_json_bytes(emitted.record))
    with _trail_and_add(context, share, dropped=True):
        with pytest.raises(rn.RunnerRefused, match="gives when run again"):
            rn.checkpointed_run(tmp_path, spec, context)
        rn.write_run(tmp_path, rn.RunOutcome(spec, record, snapshot=snapshot))
        assert rn.checkpointed_run(tmp_path, spec, context) is True


def test_a_snapshot_reads_the_composers_as_they_hold_themselves(monkeypatch, context, headline, walk_forward):
    # the armed entries and the unaccounted causes a record is built from are the composers' own
    for outcome in (headline, walk_forward):
        for strategy, composer in zip(outcome.composers, outcome.snapshot.composers, strict=True):
            assert composer.armed() == {source: decision.row.decision_at for source, decision in strategy.entry.armed.items()}
            assert composer.entry_rows == strategy.entry.run_rows() and composer.management_rows == strategy.ledger
    for where in ("entry", "management", "followup"):
        _spec, outcome = _injected_golden(monkeypatch, context, where)
        (strategy,) = outcome.composers
        own = {f"entry:{instant}:{code}" for instant, code in strategy.entry.unaccounted_causes()}
        own |= {f"management:{instant}:{code}" for instant, code in strategy.unaccounted_causes()}
        assert outcome.record["unaccounted"] == sorted(own) and own
    # a cause in the seeded history counts too, as the composer's own ledger holds it
    rows = context.history["BITSTAMP"]
    seeded = (replace(rows[0], unaccounted=("SEEDED_CAUSE",)), *rows[1:])
    record = rn.run_record(rn.RunSpec(rn.HEADLINE, "BITSTAMP", rn.CHAMPION, "base"), replace(context, history={"BITSTAMP": seeded}), headline.snapshot)
    assert record["unaccounted"] == [f"entry:{rows[0].decision_at.isoformat()}:SEEDED_CAUSE"]


def test_a_history_file_must_be_its_bindings_and_hold_every_instant(tmp_path, context):
    workspace = rn.Workspace(tmp_path)
    rows = context.history["BITSTAMP"]
    good = rn.history_binding(context, "BITSTAMP", LAST)

    def written(binding, held):
        rn._write_whole(rn.history_file(workspace, "BITSTAMP"), pickle.dumps({"binding": binding, "rows": held}))
        return lambda: rn.read_history(workspace, "BITSTAMP", context, LAST)

    assert written(good, rows)() == tuple(rows)
    for binding, held in ((good, ()), (good, rows[:-1]), (good, (*rows[:3], *rows[4:])), ({**good, "context": {"x": 1}}, rows), ({**good, "venue": "COINBASE"}, rows)):
        with pytest.raises(rn.RunnerRefused, match="HISTORY_REFUSED"):
            written(binding, held)()
    rn.history_file(workspace, "BITSTAMP").write_bytes(pickle.dumps(()))
    with pytest.raises(rn.RunnerRefused, match="HISTORY_REFUSED"):
        rn.read_history(workspace, "BITSTAMP", context, LAST)


def test_a_cold_start_differs_from_the_continuous_history(context, markets):
    seeded = rn.RegisteredEntryComposer(
        markets["BITSTAMP"], variant=context.registry.variants[rn.CHAMPION], registry=context.registry, history=context.seed("BITSTAMP", START)
    ).decide(START)
    cold = ec.EntryComposer(markets["BITSTAMP"], strategy_config=CONFIG).decide(START)
    reference = {row.decision_at: row for row in context.history["BITSTAMP"]}[START]
    assert seeded.row.regime == reference.regime
    assert cold.row.regime["previous_smoothed_score"] is None and seeded.row.regime["previous_smoothed_score"] is not None


def test_engine_events_are_counted_with_each_refusals_reasons():
    # RBT-006's surfaced point: entry conviction 72 has no risk band below 80, so its runs report the engine's outcomes
    def event(event_type, action, status, *reasons):
        return SimpleNamespace(event_type=event_type, action=action, status=status, reason_codes=reasons)

    first = SimpleNamespace(events=(event("INTENT", "ARM_ENTRY", "QUEUED"), event("INTENT", "ARM_ENTRY", "REFUSED", "A", "B")))
    second = SimpleNamespace(events=(event("INTENT", "ARM_ENTRY", "QUEUED"), event("ENTRY_EXECUTION", "ARM_ENTRY", "EXECUTED")))
    assert rn.event_counts([first, second]) == {
        "ENTRY_EXECUTION:ARM_ENTRY:EXECUTED": 1,
        "INTENT:ARM_ENTRY:QUEUED": 2,
        "INTENT:ARM_ENTRY:REFUSED:A,B": 1,
    }


# --- owner ruling 8: the engine's fee and funding checks under 28-digit rounding ---------------------

RULING_8_START = utc(2024, 1, 1)
FEE_MESSAGE = "account fees do not reconcile with trade evidence"
FUNDING_MESSAGE = "account funding does not reconcile with trade evidence"
# each found by search on the two round trips below: the totals' order of addition rounds differently
ROUNDING_FEE_BPS = "9.87654321987654321987654321"
ROUNDING_FUNDING_BPS = "2.123456789012345678901234567"
ROUNDING_BOTH_BPS = ("9.64199666597511634889612635", "1.90553592925370077597764620")


def _two_round_trips(fee_bps: str = "10", funding_bps: str = "0"):
    """Two entries and exits on flat synthetic daily bars, as the BTC-180 engine tests build them."""

    from btc_predictor.backtest.engine import ARM_ENTRY_ACTION, EXIT_ACTION, BacktestIntent, run_backtest
    from btc_predictor.config.strategy import load_strategy_config
    from btc_predictor.data import OhlcvBar
    from btc_predictor.portfolio.account import ExecutionCosts
    from btc_predictor.risk.stop import calculate_initial_stop

    config = load_strategy_config()

    def bar(day):
        timestamp = RULING_8_START + day * DAY
        return OhlcvBar(
            timestamp=timestamp, exchange="coinbase", symbol="BTC-USD", timeframe="1d", open=Decimal("100000"), high=Decimal("101000"),
            low=Decimal("99000"), close=Decimal("100500"), volume=Decimal("100"), provider="coinbase", ingested_at=timestamp + DAY,
        )

    stop = calculate_initial_stop(
        invalidation_price=Decimal("95000"), buffer=Decimal("0"), direction="long", entry_price=Decimal("101000"), config_metadata=config.run_metadata()
    )

    def strategy(context):
        day = (context.bar.timestamp - RULING_8_START) // DAY
        if day in (0, 5) and not context.position_open:
            return BacktestIntent(
                action=ARM_ENTRY_ACTION, entry_zone_lower=Decimal("99000"), entry_zone_upper=Decimal("101000"), initial_stop=stop, entry_conviction=Decimal("90")
            )
        if day in (3, 8) and context.position_open:
            return BacktestIntent(action=EXIT_ACTION, exit_reason="HOLD_SCORE_COLLAPSE")
        return None

    costs = ExecutionCosts(
        policy_version="EXECUTION_COST_V1", fee_bps=Decimal(fee_bps), slippage_bps=Decimal("0"), funding_cost_bps_per_day=Decimal(funding_bps)
    )
    return run_backtest(
        tuple(bar(day) for day in range(12)), strategy=strategy, starting_nav="1000000", strategy_config=config, strategy_id="rbt007-ruling-8", costs=costs
    )


def _in_order(items):
    total = Decimal("0")
    for item in items:
        total += item
    return total


def test_the_engine_refuses_rounding_in_the_order_of_addition_and_ruling_8_accepts_it():
    from btc_predictor.backtest import engine as backtest_engine

    original = backtest_engine._validate_result
    # the frozen engine alone: two round trips whose fees or funding have 28 significant digits refuse
    assert rn.engine_rounding([_two_round_trips()]) == {"fees": 0, "funding": 0}
    with pytest.raises(ValueError, match=f"^{FEE_MESSAGE}$"):
        _two_round_trips(ROUNDING_FEE_BPS)
    with pytest.raises(ValueError, match=f"^{FUNDING_MESSAGE}$"):
        _two_round_trips(funding_bps=ROUNDING_FUNDING_BPS)
    with pytest.raises(ValueError, match=f"^{FEE_MESSAGE}$"):
        _two_round_trips(*ROUNDING_BOTH_BPS)

    with rn.engine_rounding_rule():
        assert backtest_engine._validate_result is not original
        fee = _two_round_trips(ROUNDING_FEE_BPS)
        funding = _two_round_trips(funding_bps=ROUNDING_FUNDING_BPS)
        both = _two_round_trips(*ROUNDING_BOTH_BPS)
        with rn.engine_rounding_rule():  # nested: the same rule, kept when the inner block ends
            pass
        assert getattr(backtest_engine._validate_result, "owner_ruling_8", False)
        assert fee.as_record()["evidence_digest"] == fee.evidence_digest  # the engine's own record check, re-validated
        assert both.as_record()["evidence_digest"] == both.evidence_digest
    assert backtest_engine._validate_result is original

    assert rn.engine_rounding([fee]) == {"fees": 1, "funding": 0}
    assert rn.engine_rounding([funding]) == {"fees": 0, "funding": 1}
    assert rn.engine_rounding([both]) == {"fees": 1, "funding": 1}
    assert rn.engine_rounding([fee, funding, both]) == {"fees": 2, "funding": 2}
    for result in (fee, both):
        fills = [fill.fee for trade in result.trades for fill in trade.fills]
        assert len(result.trades) == 2 and result.account.fees_paid == _in_order(fills)
        assert sum((trade.fees for trade in result.trades), Decimal("0")) != result.account.fees_paid
        assert max(len(item.as_tuple().digits) for item in fills) == 28
        assert rn.engine_rounding_refusal(result, FEE_MESSAGE) is None
    for result in (funding, both):
        charges = [event.funding_cost for trade in result.trades for event in trade.funding_events]
        assert result.account.funding_paid == _in_order(charges)
        assert rn.engine_rounding_refusal(result, FUNDING_MESSAGE) is None
    # outside the rule the engine refuses the same result again
    with pytest.raises(ValueError, match=f"^{FEE_MESSAGE}$"):
        fee.as_record()


def test_ruling_8_refuses_anything_but_the_order_of_addition():
    from dataclasses import dataclass
    from decimal import localcontext

    @dataclass(frozen=True)
    class Account:
        fees_paid: Decimal
        funding_paid: Decimal = Decimal("0")

    @dataclass(frozen=True)
    class Result:
        account: Account
        trades: tuple

    def trade(*fees, total=None, funding=()):
        fills = tuple(SimpleNamespace(fee=Decimal(item)) for item in fees)
        events = tuple(SimpleNamespace(funding_cost=Decimal(item)) for item in funding)
        return SimpleNamespace(
            fills=fills, fees=_in_order(fill.fee for fill in fills) if total is None else Decimal(total), funding_events=events, funding=_in_order(event.funding_cost for event in events)
        )

    trades = (trade("1.5", "2.25"), trade("0.125"))
    exact = Result(Account(Decimal("3.875")), trades)
    assert rn.engine_rounding_refusal(exact, FEE_MESSAGE) is None
    assert rn.engine_rounding_refusal(exact, "ending_nav does not match final marked equity") == "not an engine fee or funding check"
    assert rn.engine_rounding_refusal(Result(Account(Decimal("3.875000000000001")), trades), FEE_MESSAGE) == "the account's total is not its charges added in order"
    assert rn.engine_rounding_refusal(Result(Account(Decimal("3.875")), (trade("1.5", "2.25", total="3.7"), trade("0.125"))), FEE_MESSAGE) == (
        "a trade's total is not its own charges added in order"
    )
    # in-order sums within each total, yet rounding beyond the engine's tolerance (a 3-digit context exaggerates it)
    with localcontext() as coarse:
        coarse.prec = 3
        coarse_trades = (trade("1.00", "0.004"), trade("0.004", "0.004"))
        coarse_result = Result(Account(_in_order([Decimal("1.00"), Decimal("0.004"), Decimal("0.004"), Decimal("0.004")])), coarse_trades)
        assert rn.engine_rounding_refusal(coarse_result, FEE_MESSAGE) == "the trades' total differs from the account's by more than the engine's tolerance"
    # funding reads each trade's funding events, not its fills
    funded = (trade("1", funding=("0.5", "0.25")), trade("1", funding=("0.125",)))
    assert rn.engine_rounding_refusal(Result(Account(Decimal("2"), Decimal("0.875")), funded), FUNDING_MESSAGE) is None
    assert rn.engine_rounding_refusal(Result(Account(Decimal("2"), Decimal("0.75")), funded), FUNDING_MESSAGE) == "the account's total is not its charges added in order"

    # the loop: an accepted check runs the engine's check again with the trades' total; anything else is the engine's
    calls = []

    def engine_check(result):
        calls.append(result)
        if len(calls) == 1:
            raise ValueError(FEE_MESSAGE)
        raise ValueError("summary counters must reconcile with event evidence")

    rounded = Result(Account(Decimal("3.875")), trades)
    with pytest.raises(ValueError, match="^summary counters must reconcile"):
        rn.validate_engine_result(rounded, engine_check)
    assert calls[0] is rounded and calls[1] is not rounded and calls[1].account.fees_paid == Decimal("3.875") and rounded.account.fees_paid == Decimal("3.875")
    staged = [FEE_MESSAGE, FUNDING_MESSAGE, None]
    passes = []

    def fee_then_funding(result):
        message = staged[len(passes)]
        passes.append(result.account)
        if message is not None:
            raise ValueError(message)

    assert rn.validate_engine_result(Result(Account(Decimal("2"), Decimal("0.875")), funded), fee_then_funding) is None
    assert passes == [Account(Decimal("2"), Decimal("0.875"))] * 3
    other = ValueError("events must be in deterministic chronological order")

    def refuses_otherwise(result):
        raise other

    with pytest.raises(ValueError) as caught:
        rn.validate_engine_result(rounded, refuses_otherwise)
    assert caught.value is other

    def refuses_again(result):
        raise ValueError(FEE_MESSAGE)

    with pytest.raises(ValueError, match=f"^{FEE_MESSAGE}$"):
        rn.validate_engine_result(rounded, refuses_again)  # accepted once; the same refusal after it is the engine's
    with pytest.raises(ValueError, match=r"the account's total is not its charges added in order \(owner ruling 8\)") as refused:
        rn.validate_engine_result(Result(Account(Decimal("4")), trades), refuses_again)
    assert str(refused.value.__cause__) == FEE_MESSAGE


def test_ruling_8_leaves_every_other_engine_check_to_the_engine():
    from btc_predictor.backtest import engine as backtest_engine

    with rn.engine_rounding_rule():
        fee = _two_round_trips(ROUNDING_FEE_BPS)
        both = _two_round_trips(*ROUNDING_BOTH_BPS)
        # a check after the fee check still refuses: the second pass is the engine's whole check
        with pytest.raises(ValueError, match="^summary counters must reconcile with event evidence$"):
            backtest_engine._validate_result(replace(fee, missed_entries=fee.missed_entries + 1))
        with pytest.raises(ValueError, match="^summary counters must reconcile with event evidence$"):
            backtest_engine._validate_result(replace(both, missed_entries=both.missed_entries + 1))
        # an account total that is not its fills added in order is refused, with the engine's refusal as its cause
        moved = replace(fee, account=replace(fee.account, fees_paid=fee.account.fees_paid + Decimal("1E-20")))
        with pytest.raises(ValueError, match=r"not its charges added in order \(owner ruling 8\)"):
            backtest_engine._validate_result(moved)
        # a check before the fee check is the engine's, unchanged
        with pytest.raises(ValueError, match="^ending_nav does not match final marked equity$"):
            backtest_engine._validate_result(replace(fee, ending_nav=fee.ending_nav + 1))


def test_main_runs_the_backtest_under_ruling_8(monkeypatch, tmp_path):
    from btc_predictor.backtest import engine as backtest_engine
    from btc_predictor.research_backtest import backfill_run
    from btc_predictor.research_backtest import dataset_build as build

    original = backtest_engine._validate_result
    seen = []

    def execute_all(context, specs, workspace, **kwargs):
        seen.append((getattr(backtest_engine._validate_result, "owner_ruling_8", False), len(specs)))
        raise rn.RunnerRefused("RUN_REFUSED", "stopped by the test")

    monkeypatch.setattr(rn, "fresh_bytecode_process", lambda: True)
    monkeypatch.setattr(rn, "require_fresh_bytecode", lambda: str(tmp_path))
    monkeypatch.setattr(build, "code_commit", lambda repository=None: "0" * 40)
    monkeypatch.setattr(rn, "require_frozen_code", lambda repository, commit: ([], set()))
    monkeypatch.setattr(rn, "verify_preregistration", lambda *args: None)
    monkeypatch.setattr(backfill_run, "EvidenceStore", lambda root, public_repository: SimpleNamespace(root=root))
    monkeypatch.setattr(rn, "load_frozen_inputs", lambda store: SimpleNamespace(inputs={"BITSTAMP": None}, private_commit="p", index_sha256="i"))
    monkeypatch.setattr(rn, "execute_all", execute_all)
    lines = []
    assert rn.main(["run", "--store", str(tmp_path), "--workers", "1"], out=lines.append) == 2
    assert seen and seen[0][0] is True and seen[0][1] > 0
    assert lines[-1] == "refused: RUN_REFUSED: stopped by the test"
    assert backtest_engine._validate_result is original


# --- owner ruling 9: the BTC-183 and BTC-184 row checks under 28-digit rounding ----------------------

BUCKET_MESSAGE = "bucket P&L does not reconcile"
SETUP_PNL_MESSAGE = "setup P&L does not reconcile"
COSTS_MESSAGE = "setup costs do not reconcile"
# each found by search on the owners' own synthetic walk-forward runs: (strategy, fee bps, funding bps, test periods)
ROUNDING_PNL = ("enter_and_hold", "6.26018159083016613186091390", "0", 2)  # four open trades: bucket and setup P&L
ROUNDING_COSTS = ("enter_then_exit", "5.36469748212378991433014673", "1.02458921527589290075400917", 3)  # three closed trades: costs
ROUNDING_ROW = ("enter_and_hold", "6.91289494616467631239538346", "3.75669245185261999618842087", 3)  # one setup row: P&L and costs


def _owner_reports(strategy="enter_and_hold", fee_bps="10", funding_bps="0", test_periods=2):
    """A walk-forward run's BTC-183 breakdown and BTC-184 report, as those owners' own tests build them."""

    from btc_predictor.backtest import run_regime_performance_breakdown, run_walk_forward, setup_performance_report_from_breakdown, walk_forward_plan
    from btc_predictor.portfolio.account import ExecutionCosts
    from btc_predictor.tests import test_backtest_regime_performance as owner_tests

    costs = ExecutionCosts(
        policy_version="EXECUTION_COST_V1", fee_bps=Decimal(fee_bps), slippage_bps=Decimal("0"), funding_cost_bps_per_day=Decimal(funding_bps)
    )
    plan = walk_forward_plan(owner_tests.CONFIG, train_periods=3, test_periods=test_periods, step_periods=test_periods)
    source = run_walk_forward(
        owner_tests.BARS,
        strategy_factory=owner_tests.factory(getattr(owner_tests, strategy)),
        plan=plan,
        starting_nav=owner_tests.NAV,
        strategy_config=owner_tests.CONFIG,
        costs=costs,
    )
    breakdown = run_regime_performance_breakdown(source, owner_tests.contexts_for(source))
    return breakdown, setup_performance_report_from_breakdown(breakdown)


def _buckets(breakdown):
    return (breakdown.overall, *(bucket for item in breakdown.breakdowns for bucket in item.buckets))


def _ruling_9_functions():
    from btc_predictor.backtest import regime_performance as regime_owner
    from btc_predictor.backtest import setup_performance as setup_owner

    return (
        regime_owner._bucket_performance,
        regime_owner._validate_bucket_performance,
        setup_owner._derive_setup_performance,
        setup_owner._validate_setup_performance,
    )


def test_the_owners_refuse_rounding_in_the_order_of_addition_and_ruling_9_accepts_it():
    from btc_predictor.backtest import regime_performance as regime_owner
    from btc_predictor.backtest import setup_performance as setup_owner

    originals = _ruling_9_functions()
    report_checks = (regime_owner._validate_result, setup_owner._validate_report)
    # the frozen owners alone: rows summed in two groupings of 28-digit values refuse
    plain_breakdown, plain = _owner_reports()
    assert rn.report_rounding(plain_breakdown, plain) == {"bucket_pnl": 0, "setup_pnl": 0, "setup_costs": 0}
    with pytest.raises(ValueError, match=f"^{BUCKET_MESSAGE}$"):
        _owner_reports(*ROUNDING_PNL)
    with pytest.raises(ValueError, match=f"^{COSTS_MESSAGE}$"):
        _owner_reports(*ROUNDING_COSTS)
    with pytest.raises(ValueError, match=f"^{BUCKET_MESSAGE}$"):
        _owner_reports(*ROUNDING_ROW)

    with rn.report_rounding_rule():
        assert all(getattr(function, "owner_ruling_9", False) for function in _ruling_9_functions())
        pnl_breakdown, pnl = _owner_reports(*ROUNDING_PNL)
        costs_breakdown, costs = _owner_reports(*ROUNDING_COSTS)
        row_breakdown, row_report = _owner_reports(*ROUNDING_ROW)
        installed, noted = _ruling_9_functions(), dict(rn._REPORT_ROWS)
        assert noted and all(verdict is None for verdict in noted.values())
        with rn.report_rounding_rule():  # nested: the same rule and its noted rows, kept when the inner block ends
            assert _ruling_9_functions() == installed and rn._REPORT_ROWS == noted
        assert _ruling_9_functions() == installed and rn._REPORT_ROWS == noted
        # the two report-level checks stay the owners'
        assert (regime_owner._validate_result, setup_owner._validate_report) == report_checks
        # the owners' own record checks, run again: every report and its digest unchanged
        for report in (pnl_breakdown, pnl, costs_breakdown, costs, row_breakdown, row_report):
            assert report.as_record()["evidence_digest"] == report.evidence_digest
        for breakdown in (pnl_breakdown, row_breakdown):
            refused = [bucket for bucket in _buckets(breakdown) if bucket.total_pnl != bucket.realized_net_pnl + bucket.marked_unrealized_pnl]
            assert refused and all(rn.report_rounding_refusal(bucket, BUCKET_MESSAGE) is None for bucket in refused)
        (costs_row,) = [item for item in costs.setups if item.trade_count]
        (both_row,) = [item for item in row_report.setups if item.trade_count]
        assert rn.report_rounding_refusal(costs_row, COSTS_MESSAGE) is None
        assert rn.report_rounding_refusal(both_row, SETUP_PNL_MESSAGE) is None and rn.report_rounding_refusal(both_row, COSTS_MESSAGE) is None
    assert _ruling_9_functions() == originals
    assert rn._REPORT_ROWS == {}

    assert rn.report_rounding(pnl_breakdown, pnl) == {"bucket_pnl": 5, "setup_pnl": 1, "setup_costs": 0}
    assert rn.report_rounding(costs_breakdown, costs) == {"bucket_pnl": 0, "setup_pnl": 0, "setup_costs": 1}
    assert rn.report_rounding(row_breakdown, row_report) == {"bucket_pnl": 5, "setup_pnl": 1, "setup_costs": 1}
    # each accepted row's totals are its own trades' values added in order, carrying 28 significant digits
    attributions = pnl_breakdown.attributions
    overall = pnl_breakdown.overall
    assert len(attributions) == 4 and not any(item.closed for item in attributions)
    fields = ("total_pnl", "realized_net_pnl", "marked_unrealized_pnl")
    assert tuple(getattr(overall, field) for field in fields) == tuple(_in_order(getattr(item, field) for item in attributions) for field in fields)
    assert overall.total_pnl != overall.realized_net_pnl + overall.marked_unrealized_pnl
    assert max(len(item.realized_net_pnl.as_tuple().digits) for item in attributions) == 28
    for breakdown, row in ((costs_breakdown, costs_row), (row_breakdown, both_row)):
        assert all(len(fold.result.trades) == 1 for fold in breakdown.validation.folds)
        trades = [fold.result.trades[0] for fold in breakdown.validation.folds]
        assert row.trade_count == len(trades) == 3 and all(trade.funding != 0 for trade in trades)
        assert (row.fees, row.funding, row.total_costs) == (
            _in_order(trade.fees for trade in trades),
            _in_order(trade.funding for trade in trades),
            _in_order(trade.fees + trade.funding for trade in trades),
        )
        assert row.total_costs != row.fees + row.funding
    assert all(trade.closed for trade in (fold.result.trades[0] for fold in costs_breakdown.validation.folds))
    # outside the rule the owners refuse the same reports again
    with pytest.raises(ValueError, match=f"^{BUCKET_MESSAGE}$"):
        pnl_breakdown.as_record()
    with pytest.raises(ValueError, match=f"^{COSTS_MESSAGE}$"):
        costs.as_record()


def test_ruling_9_refuses_anything_but_the_order_of_addition():
    from decimal import localcontext

    from btc_predictor.backtest import regime_performance as regime_owner

    def attribution(realized, marked, total=None):
        realized, marked = Decimal(realized), Decimal(marked)
        return SimpleNamespace(
            closed=False, realized_net_pnl=realized, marked_unrealized_pnl=marked, total_pnl=realized + marked if total is None else Decimal(total), r_multiple=None
        )

    with rn.report_rounding_rule():
        # a 3-digit context: the bucket's two groupings differ by far more than the engine's tolerance
        with localcontext() as coarse:
            coarse.prec = 3
            wide = regime_owner._bucket_performance("overall", "ALL", (attribution("1.00", "1.00"), attribution("0.004", "0.004")))
        assert (wide.total_pnl, wide.realized_net_pnl, wide.marked_unrealized_pnl) == (Decimal("2.01"), Decimal("1.00"), Decimal("1.00"))
        assert rn.report_rounding_refusal(wide, BUCKET_MESSAGE) == "the row's total differs from the sum of its parts by more than the engine's tolerance"
        with pytest.raises(ValueError, match=r"^bucket P&L does not reconcile: the row's total differs .* \(owner ruling 9\)$") as refused:
            regime_owner._validate_bucket_performance(wide)
        assert str(refused.value.__cause__) == BUCKET_MESSAGE
        assert rn.report_rounding_refusal(wide, "bucket trade counts do not reconcile") == "not an owner row check under ruling 9"
        # a row whose check passes is not noted at all
        exact = regime_owner._bucket_performance("overall", "ALL", (attribution("1.5", "2.25"), attribution("0.125", "0")))
        assert exact.total_pnl == exact.realized_net_pnl + exact.marked_unrealized_pnl
        assert rn.report_rounding_refusal(exact, BUCKET_MESSAGE) == "the row's totals are not its own trades' values added in order"

        _row_breakdown, row_report = _owner_reports(*ROUNDING_ROW)
        costs_breakdown, costs = _owner_reports(*ROUNDING_COSTS)
        (row,) = [item for item in row_report.setups if item.trade_count]
        (costs_row,) = [item for item in costs.setups if item.trade_count]
        # a total that is not its own trades' values added in order, or parts that are not, are refused
        for moved, message in (
            (replace(costs_row, total_costs=costs_row.total_costs + Decimal("1E-20")), COSTS_MESSAGE),
            (replace(costs_row, funding=costs_row.funding + Decimal("1E-20")), COSTS_MESSAGE),
            (replace(row, total_pnl=row.total_pnl + Decimal("1E-20")), SETUP_PNL_MESSAGE),
            (replace(row, setup=next(name for name in rn.setup_owner.SETUP_BUCKETS if name != row.setup)), SETUP_PNL_MESSAGE),
        ):
            assert rn.report_rounding_refusal(moved, message) == "the row's totals are not its own trades' values added in order"
        # a setup's costs are its own trades', found from the breakdown's attributions as the owner finds them
        trades = rn._setup_trades(costs_breakdown)
        assert trades[costs_row.setup] == [fold.result.trades[0] for fold in costs_breakdown.validation.folds]
        assert sum(len(items) for items in trades.values()) == costs_row.trade_count
        first, *rest = costs_breakdown.attributions
        for changed in (
            replace(first, fold_number=99),
            replace(first, trade_number=0),
            replace(first, trade_number=2),
            replace(first, setup="NO_SUCH_SETUP"),
            replace(first, trade_evidence_digest="0" * 64),
        ):
            assert rn._setup_trades(replace(costs_breakdown, attributions=(changed, *rest))) is None
    # outside the rule nothing is noted, so nothing is accepted
    assert rn.report_rounding_refusal(costs_row, COSTS_MESSAGE) == "the row's totals are not its own trades' values added in order"


def test_ruling_9_runs_the_owners_whole_row_check_again():
    from btc_predictor.backtest import regime_performance as regime_owner
    from btc_predictor.backtest import setup_performance as setup_owner

    with rn.report_rounding_rule():
        row_breakdown, row_report = _owner_reports(*ROUNDING_ROW)
        (row,) = [item for item in row_report.setups if item.trade_count]
        bucket = row_breakdown.overall
        # the real owners' row checks: both of a setup row's checks accepted in turn, its other conditions still the owner's
        setup_owner._validate_setup_performance(row)
        regime_owner._validate_bucket_performance(bucket)
        with pytest.raises(ValueError, match="^setup outcome signs are invalid$"):  # after the costs check
            setup_owner._validate_setup_performance(replace(row, closed_net_loss=Decimal("1")))
        with pytest.raises(ValueError, match="^setup trade counts do not reconcile$"):  # before both
            setup_owner._validate_setup_performance(replace(row, trade_count=row.trade_count + 1))
        with pytest.raises(ValueError, match="^win-rate availability must match closed-trade count$"):  # after the P&L check
            regime_owner._validate_bucket_performance(replace(bucket, closed_trade_win_rate=Decimal("1")))
        with pytest.raises(ValueError, match="^bucket closed-trade outcomes do not reconcile$"):  # before it
            regime_owner._validate_bucket_performance(replace(bucket, winning_closed_trades=1))
        moved = replace(row, total_costs=row.total_costs + Decimal("1E-20"))
        with pytest.raises(ValueError, match=r"^setup costs do not reconcile: the row's totals are not .* \(owner ruling 9\)$") as refused:
            setup_owner._validate_setup_performance(moved)
        assert str(refused.value.__cause__) == COSTS_MESSAGE

        # the loop: each accepted check runs the owner's check again on a copy holding the sum of the parts
        passes = []

        def staged(*messages):
            def check(item):
                passes.append(item)
                message = messages[len(passes) - 1]
                if message is not None:
                    raise ValueError(message)

            return check

        assert rn.validate_report_row(row, staged(SETUP_PNL_MESSAGE, COSTS_MESSAGE, None), rn._SETUP_CHECKS) is None
        assert passes[0] is row and passes[1].total_pnl == row.realized_net_pnl + row.marked_unrealized_pnl
        assert passes[1].total_costs == row.total_costs and passes[2].total_costs == row.fees + row.funding
        assert passes[2].total_pnl == passes[1].total_pnl and row.total_pnl != passes[1].total_pnl  # the row itself unchanged
        passes.clear()
        with pytest.raises(ValueError, match=f"^{SETUP_PNL_MESSAGE}$"):  # accepted once; the same refusal after it is the owner's
            rn.validate_report_row(row, staged(SETUP_PNL_MESSAGE, SETUP_PNL_MESSAGE), rn._SETUP_CHECKS)
        other = ValueError("setup closed-trade outcomes do not reconcile")

        def refuses_otherwise(item):
            raise other

        with pytest.raises(ValueError) as caught:
            rn.validate_report_row(row, refuses_otherwise, rn._SETUP_CHECKS)
        assert caught.value is other
        passes.clear()
        with pytest.raises(ValueError, match=f"^{COSTS_MESSAGE}$"):  # a check the validator's own list does not name
            rn.validate_report_row(row, staged(COSTS_MESSAGE), rn._BUCKET_CHECKS)


def test_main_runs_the_backtest_under_ruling_9(monkeypatch, tmp_path):
    from btc_predictor.research_backtest import backfill_run
    from btc_predictor.research_backtest import dataset_build as build

    originals = _ruling_9_functions()
    seen = []

    def execute_all(context, specs, workspace, **kwargs):
        seen.append(all(getattr(function, "owner_ruling_9", False) for function in _ruling_9_functions()))
        raise rn.RunnerRefused("RUN_REFUSED", "stopped by the test")

    monkeypatch.setattr(rn, "fresh_bytecode_process", lambda: True)
    monkeypatch.setattr(rn, "require_fresh_bytecode", lambda: str(tmp_path))
    monkeypatch.setattr(build, "code_commit", lambda repository=None: "0" * 40)
    monkeypatch.setattr(rn, "require_frozen_code", lambda repository, commit: ([], set()))
    monkeypatch.setattr(rn, "verify_preregistration", lambda *args: None)
    monkeypatch.setattr(backfill_run, "EvidenceStore", lambda root, public_repository: SimpleNamespace(root=root))
    monkeypatch.setattr(rn, "load_frozen_inputs", lambda store: SimpleNamespace(inputs={"BITSTAMP": None}, private_commit="p", index_sha256="i"))
    monkeypatch.setattr(rn, "execute_all", execute_all)
    lines = []
    assert rn.main(["run", "--store", str(tmp_path), "--workers", "1"], out=lines.append) == 2
    assert seen == [True]
    assert lines[-1] == "refused: RUN_REFUSED: stopped by the test"
    assert _ruling_9_functions() == originals


def test_sweep_runs_execute_on_the_base_rungs_costs(context, share):
    variant = next(variant for variant in context.registry.variants.values() if variant.role == rn.SWEEP)
    with share():
        outcome = rn.execute_run(rn.RunSpec(rn.SWEEP, "BITSTAMP", variant.variant_id, "base"), context)
    assert outcome.validation.cost_profile is None
    assert outcome.validation.effective_costs.as_record() == cost_profile("base", config=variant.config).costs.as_record()


# --- metrics (the frozen definitions) ---------------------------------------------------------------


def test_the_run_view_keeps_btc182s_aggregate_conventions(walk_forward):
    validation = walk_forward.validation
    view = rm.validation_view(validation)
    assert view.mean_return_fraction == validation.mean_return_fraction
    assert view.summed_net_pnl == validation.summed_net_pnl
    assert view.worst_fold.fold_number == validation.worst_fold.fold_number
    assert view.best_fold.fold_number == validation.best_fold.fold_number
    assert [fold.return_fraction for fold in view.folds] == [fold.return_fraction for fold in validation.folds]


def _equity(points, *, start=utc(2024, 1, 1), nav="100"):
    curve = tuple(SimpleNamespace(as_of=start + timedelta(hours=hour), nav=Decimal(value)) for hour, value in points)
    result = SimpleNamespace(equity_curve=curve, started_at=start)
    return SimpleNamespace(starting_nav=Decimal(nav), result=result, fold_number=1)


def test_the_longest_drawdown_follows_its_frozen_definition():
    # drawdown from the starting NAV at started_at, recovered at hour 5
    assert rm._fold_longest_drawdown(_equity([(1, "99"), (3, "98"), (5, "100"), (6, "101")])) == (Decimal(5), True)
    # an unrecovered drawdown ends at the last point; the at-peak instant is that point's as_of
    assert rm._fold_longest_drawdown(_equity([(1, "101"), (2, "100"), (9, "100.5")])) == (Decimal(8), False)
    # equal lengths: the first is reported, recovered, before an equally long unrecovered one
    assert rm._fold_longest_drawdown(_equity([(1, "99"), (2, "100"), (3, "99"), (4, "99.5")])) == (Decimal(2), True)
    # never strictly below the running peak: zero hours, and no recovery mark (review F12)
    assert rm._fold_longest_drawdown(_equity([(1, "100"), (2, "100"), (3, "102")])) == (Decimal(0), None)


def test_the_longest_drawdown_gives_every_frozen_example(preregistration):
    metric = next(item for item in preregistration["report"]["metric_spec"]["metrics"] if item["metric"] == "longest_drawdown")
    assert len(metric["examples"]) == 6
    for example in metric["examples"]:
        fold = _equity([(int(hour), nav) for hour, nav in example["points"]], nav=example["starting_nav"])
        assert rm._fold_longest_drawdown(fold) == (Decimal(example["hours"]), example["recovered"]), example["case"]
        reported = rm._longest_drawdown(rm.RunView((fold,)))
        assert (Decimal(reported["value"]), reported["recovered"]) == (Decimal(example["hours"]), example["recovered"]), example["case"]


def test_the_memory_check_finds_a_history_that_differs(context, headline):
    altered = []
    for row in context.history["BITSTAMP"]:
        if row.decision_at == utc(2024, 4, 1):
            row = replace(row, capitulation_flag_state=not row.capitulation_flag_state)
        altered.append(row)
    check = rn.memory_check(replace(context, history={"BITSTAMP": tuple(altered)}), "BITSTAMP", headline.composers)
    assert check["mismatches"] == ["2024-04-01T00:00:00+00:00"] and not check["matches_history"]


def test_sortino_statuses():
    assert rm._sortino((Decimal("0.1"),), "AVAILABLE") == (None, rm.INSUFFICIENT_PERIODS)
    assert rm._sortino((Decimal("0.1"), Decimal("0.2")), "AVAILABLE") == (None, rm.NO_DOWNSIDE)
    value, status = rm._sortino((Decimal("0.1"), Decimal("-0.1")), "AVAILABLE")
    assert status == "AVAILABLE" and value == Decimal("0")
    # mean 0.05 over sqrt(0.01 / 2): the downside deviation divides by n, not n - 1
    value, _ = rm._sortino((Decimal("0.2"), Decimal("-0.1")), "AVAILABLE")
    assert value == Decimal("0.707106781187")
    assert rm._sortino((), "UNDEFINED_NON_POSITIVE_NAV") == (None, "UNDEFINED_NON_POSITIVE_NAV")


def _trade(pnl, closed_at=1, *, closed=True, notional="100"):
    return SimpleNamespace(net_pnl=Decimal(pnl), closed=closed, closed_at=utc(2024, 1, closed_at), entry_notional=Decimal(notional), exit_notional=Decimal(notional), r_multiple=None)


def test_the_trade_metrics_follow_their_definitions(walk_forward):
    trades = (_trade("10", 1), _trade("-5", 2), _trade("0", 3), _trade("-1", 4), _trade("-2", 5), _trade("4", 6, closed=False))
    view = rm.RunView((rm.FoldView(1, walk_forward.validation.folds[0].result),))
    closed = tuple(trade for trade in trades if trade.closed)
    assert rm._losing_streak(closed)["value"] == "2"  # the flat trade ends the first streak
    assert rm._losing_streak(())["value"] == "0"
    factor = rm.setups._profit_factor(closed_count=0, closed_profit=Decimal(0), closed_loss=Decimal(0))
    assert factor == (None, "NO_CLOSED_TRADES")
    assert rm.setups._profit_factor(closed_count=1, closed_profit=Decimal(1), closed_loss=Decimal(0))[1] == "UNBOUNDED_NO_CLOSED_LOSSES"
    metrics = rm.run_metrics(view)
    assert set(metrics) == set(rm.PRIMARY_METRICS)
    assert all("status" in metric for metric in metrics.values())


def test_the_trade_metric_values_follow_their_definitions():
    trades = (_trade("10", 1), _trade("-5", 2), _trade("0", 3), _trade("-1", 4), _trade("-2", 5), _trade("4", 6, closed=False))
    curve = (
        SimpleNamespace(as_of=utc(2024, 1, 1, 1), nav=Decimal("100"), open_quantity=Decimal("1")),
        SimpleNamespace(as_of=utc(2024, 1, 1, 2), nav=Decimal("99"), open_quantity=Decimal("0")),
    )
    result = SimpleNamespace(
        trades=trades,
        equity_curve=curve,
        starting_nav=Decimal("100"),
        total_pnl=Decimal("-1"),
        net_pnl=Decimal("2"),
        final_lifecycle=SimpleNamespace(quantity=Decimal("1")),
        started_at=utc(2024, 1, 1),
        ended_at=utc(2024, 1, 3),
    )
    metrics = rm.run_metrics(rm.RunView((rm.FoldView(1, result),)))
    assert metrics["win_rate"]["value"] == "0.200000000000" and metrics["win_rate"]["winning_trades"] == 1  # flat is not a win
    assert metrics["average_winner"]["value"] == "10.000000000000"
    assert Decimal(metrics["average_loser"]["value"]) == Decimal("-2.666666666667")
    assert metrics["return_per_trade"]["value"] == "0.004000000000"  # mean of net_pnl / entry_notional over closed trades
    assert metrics["profit_factor"]["value"] == str(rm.setups._ratio(Decimal(10), Decimal(8)))
    assert metrics["time_in_market"]["value"] == "0.500000000000"
    assert metrics["turnover"]["value"] == "12.060301507538" and metrics["turnover"]["run_days"] == "2.000000000000"
    assert (metrics["number_of_trades"]["trades"], metrics["number_of_trades"]["closed_trades"], metrics["number_of_trades"]["open_at_end"]) == (6, 5, 1)
    assert metrics["longest_losing_streak"]["value"] == "2"
    assert metrics["expectancy"]["value"] == str(rm.sweeps._mean(tuple(Decimal(value) for value in ("10", "-5", "0", "-1", "-2"))))


def _fake_trade(entry, stop, mfe, mae, *, closed=True, exit_reason="STRUCTURAL_STOP"):
    return SimpleNamespace(
        average_entry_price=Decimal(entry),
        initial_stop_price=Decimal(stop),
        mfe_r=Decimal(mfe),
        mae_r=Decimal(mae),
        closed=closed,
        exit_reason=exit_reason,
        exit_notional=Decimal(entry) * 2,
        fills=(SimpleNamespace(action="ENTER", quantity=Decimal(2)), SimpleNamespace(action="EXIT", quantity=Decimal(2))),
    )


def test_the_cross_venue_measures_follow_clarification_4a():
    entries = {
        "BITSTAMP": [{"decision_at": "d1", "setup": "A"}, {"decision_at": "d2", "setup": "A"}],
        "COINBASE": [{"decision_at": "d1", "setup": "A"}, {"decision_at": "d3", "setup": "B"}],
    }
    trades = {
        "BITSTAMP": [_fake_trade("100", "90", "2", "-1"), _fake_trade("100", "90", "1", "-1")],
        "COINBASE": [_fake_trade("101", "90", "1.5", "-1", exit_reason="EXIT"), _fake_trade("100", "90", "1", "-1")],
    }
    trade_entries = {"BITSTAMP": {0: "d1", 1: "d2"}, "COINBASE": {0: "d1", 1: "d3"}}
    metric = {"value": "1", "status": "AVAILABLE", "closed_trades": 4}
    undefined = {"value": None, "status": "NO_CLOSED_TRADES", "closed_trades": 0}
    metrics = {"base": {"BITSTAMP": {name: metric for name in rm.PRIMARY_METRICS}, "COINBASE": {name: undefined for name in rm.PRIMARY_METRICS}}}
    result = rm.cross_venue(entries, trades, trade_entries, metrics)
    overlap = result["trade_set_overlap"]["pairs"][0]
    assert (overlap["matched"], overlap["only_first"], overlap["only_second"]) == (1, 1, 1)
    assert Decimal(overlap["overlap"]) == (Decimal(1) / Decimal(3)).quantize(Decimal("1E-12"))
    divergence = result["matched_trade_divergence"][0]
    assert divergence["matched"] == 1 and Decimal(divergence["average_entry_price"]["mean"]) == Decimal("0.01")
    assert Decimal(divergence["mfe_r"]["mean"]) == Decimal("-0.5")
    touch = result["stop_touch_divergence"][0]
    assert (touch["matched_closed"], touch["exactly_one_structural_stop"]) == (1, 1)
    assert result["metric_dispersion"]["base"]["expectancy"]["status"] == "UNDEFINED_ON_SOME_VENUE"
    assert result["metric_dispersion"]["base"]["expectancy"]["counts"] == {"BITSTAMP": {"closed_trades": 4}, "COINBASE": {"closed_trades": 0}}
    # review F7: matching intents that filled no trade are no trades
    unfilled = rm.cross_venue(entries, {"BITSTAMP": [], "COINBASE": []}, {"BITSTAMP": {}, "COINBASE": {}}, metrics)
    overlap = unfilled["trade_set_overlap"]["pairs"][0]
    assert (overlap["matched"], overlap["only_first"], overlap["only_second"], overlap["status"]) == (0, 0, 0, "NO_TRADES")
    assert unfilled["trade_set_overlap"]["matched_on_all_venues"] == 0
    one_side = rm.cross_venue(entries, {"BITSTAMP": trades["BITSTAMP"][:1], "COINBASE": []}, {"BITSTAMP": {0: "d1"}, "COINBASE": {}}, metrics)
    overlap = one_side["trade_set_overlap"]["pairs"][0]
    assert (overlap["matched"], overlap["only_first"], overlap["only_second"], overlap["overlap"]) == (0, 1, 0, "0E-12")


# --- the look-ahead audit (ruling 3) ----------------------------------------------------------------------


def test_truncated_inputs_keep_only_what_is_available_at_the_instant(markets):
    instant = utc(2024, 3, 20)
    truncated = rn.truncated_inputs(markets["BITSTAMP"], instant)
    shared = truncated.dataset.shared_snapshot
    assert truncated.dataset.price_bars and all(bar.ingested_at <= instant for bar in truncated.dataset.price_bars)
    assert all(bar.ingested_at <= instant for bar in shared.volume_bars)
    for rows in (shared.etf_flows, shared.funding_rates, shared.open_interest, shared.perp_volumes, truncated.futures_basis, truncated.market_caps, truncated.liquidation_percentiles):
        assert rows and all(row.available_at <= instant for row in rows)
    assert len(truncated.dataset.price_bars) < len(markets["BITSTAMP"].dataset.price_bars)
    assert truncated.etf_fund_launches == markets["BITSTAMP"].etf_fund_launches


def test_the_audit_sample_is_every_intent_plus_twenty_seeded_instants():
    instants = [START + DAY * index for index in range(60)]
    intents = {instants[3], instants[10]}
    sample = rn.audit_sample("BITSTAMP", instants, intents)
    assert len(sample) == 22 and {instant for instant, reason in sample if reason == "INTENT"} == intents
    assert sample == rn.audit_sample("BITSTAMP", list(reversed(instants)), intents)
    assert sample != rn.audit_sample("COINBASE", instants, intents)


@pytest.fixture(scope="module")
def audit_state(context, headline, share):
    return rn.audit_state("BITSTAMP", context, headline.record, share=share)


def test_the_audit_state_reproduces_the_run_and_the_replay_gives_it_back(audit_state):
    assert audit_state.reproduced and audit_state.replay_reproduces_run
    assert audit_state.run_instants == [START + DAY * index for index in range((LAST - START) // DAY + 1)]
    assert audit_state.calls and set(audit_state.calls) == set(audit_state.managed)
    assert audit_state.ledger[0].decision_at == SCHEDULE[0]
    intents = {instant for instant, reason in audit_state.sample if reason == "INTENT"}
    # the synthetic window is short: its sample is every intent plus all that is left, up to 20
    assert intents and len(audit_state.sample) == min(len(audit_state.run_instants), len(intents) + rn.AUDIT_SEEDED_INSTANTS)


def test_every_link_passes_on_the_champion(context, audit_state, tmp_path):
    management = sorted(audit_state.calls)
    intent = next(instant for instant, reason in audit_state.sample if reason == "INTENT")
    for instant in sorted({START, intent, management[0], management[-1], LAST}):
        item = rn.run_link(audit_state, context, instant)
        assert not rn._link_failed(item) and item["entry_row_equal"] and item["replay_prefix_equal"] and item["engine_state_equal"], item
        assert (item["management_row_equal"] is not None) == (instant in audit_state.calls)
    for instant in (SCHEDULE[0], SCHEDULE[7], START - DAY, LAST):
        assert rn.history_link("BITSTAMP", context, instant)["entry_row_equal"]
    # a link outside ruling 3's sample may take the audit's own shared results (review ruling 3a)
    truncated = rn.truncated_inputs(context.inputs["BITSTAMP"], management[-1])
    encoder = rs.ArgumentEncoder()
    rs.register_positioning_sources(encoder, truncated)
    statistics = rs.ShareStatistics()
    with rs.shared_positioning(rs.SharedResultStore(tmp_path), encoder, statistics):
        computed = rn.run_link(audit_state, context, management[-1], truncated=truncated)
        served = rn.run_link(audit_state, context, management[-1], truncated=rn.truncated_inputs(context.inputs["BITSTAMP"], management[-1]))
    assert sum(statistics.served.values()) > 0 and not rn._link_failed(computed) and computed == served


def test_the_replay_gives_the_engine_only_the_bars_available_at_the_instant(context, audit_state, monkeypatch):
    seen = []
    real = rn.run_backtest

    def capture(bars, **kwargs):
        seen.append(max(rn._bar_available_at(bar) for bar in bars))
        return real(bars, **kwargs)

    monkeypatch.setattr(rn, "run_backtest", capture)
    instant = START + 4 * DAY
    entry, replay = rn._replay(audit_state, context, instant)
    assert seen == [instant] and max(replay.positions) == instant
    rn._replay(audit_state, context, LAST + DAY, inclusive=False)
    assert seen[-1] < LAST + DAY


def test_the_audit_catches_an_injected_look_ahead(context, share, monkeypatch):
    real = ec._DecisionRun.run

    def peeking(self):
        # each row also records the close of the first bar after its instant
        decision = real(self)
        later = [bar for bar in self.c._hourly if bar.ingested_at > self.t]
        features = {**decision.row.features, "PEEK": later[0].close if later else None}
        return replace(decision, row=replace(decision.row, features=features))

    monkeypatch.setattr(ec._DecisionRun, "run", peeking)
    with share():
        outcome = rn.execute_run(rn.RunSpec(rn.HEADLINE, "BITSTAMP", rn.CHAMPION, "base"), context)
    state = rn.audit_state("BITSTAMP", context, outcome.record, share=share)
    assert state.reproduced
    for instant in (START, START + 5 * DAY, LAST):
        item = rn.run_link(state, context, instant)
        assert not item["entry_row_equal"] and rn._link_failed(item)


def test_a_contaminated_history_row_fails_its_own_link(context):
    # review F2: a later value carried into the market memory before the window passed the sampled audit
    instant = START - 5 * DAY
    rows = context.history["BITSTAMP"]
    position = next(index for index, row in enumerate(rows) if row.decision_at == instant)
    regime = dict(rows[position].regime)
    regime["smoothed_score"] = "99.5"
    tampered = (*rows[:position], replace(rows[position], regime=regime), *rows[position + 1 :])
    contaminated = replace(context, history={"BITSTAMP": tampered})
    assert not rn.history_link("BITSTAMP", contaminated, instant)["entry_row_equal"]
    assert rn.history_link("BITSTAMP", context, instant)["entry_row_equal"]


def test_an_engine_state_not_from_the_available_bars_fails_its_link(context, share, monkeypatch):
    real = rn.RecordingManagementComposer.decide

    def elsewhere(self, decision, *, lifecycle, nav, armed, prior_flow):
        # management receives a NAV the engine never computed from the bars available
        return real(self, decision, lifecycle=lifecycle, nav=nav + 1, armed=armed, prior_flow=prior_flow)

    monkeypatch.setattr(rn.RecordingManagementComposer, "decide", elsewhere)
    with share():
        outcome = rn.execute_run(rn.RunSpec(rn.HEADLINE, "BITSTAMP", rn.CHAMPION, "base"), context, record_management=True)
    state = rn.audit_state("BITSTAMP", context, outcome.record, share=share)
    assert state.reproduced and not state.replay_reproduces_run
    item = rn.run_link(state, context, min(state.calls))
    assert item["engine_state_equal"] is False and rn._link_failed(item)


def test_the_audit_summary_needs_every_link_once_and_an_unshared_sample():
    history = [START - DAY, START]
    second = (START + DAY).isoformat()
    expected = {"run_instants": [START.isoformat(), second], "sample": [[START.isoformat(), "INTENT"]], "managed": [second]}
    meta = {"reproduced": True, "replay_reproduces_run": True, "run_instants": expected["run_instants"], "sample": expected["sample"]}
    checks = {"entry_row_equal": True, "intent_equal": True, "composition_equal": True, "replay_prefix_equal": True, "engine_state_equal": True}
    good = [
        {"venue": "V", "kind": rn.HISTORY_LINK, "decision_at": (START - DAY).isoformat(), "entry_row_equal": True, "shared": True},
        {"venue": "V", "kind": rn.HISTORY_LINK, "decision_at": START.isoformat(), "entry_row_equal": True, "shared": True},
        {"venue": "V", "kind": rn.RUN_LINK, "decision_at": START.isoformat(), "sample": "INTENT", **checks, "management_row_equal": None, "shared": False},
        {"venue": "V", "kind": rn.RUN_LINK, "decision_at": second, "sample": None, **checks, "management_row_equal": True, "shared": True},
    ]

    def passed(links=good, meta=meta, expected=expected):
        return rn.audit_summary("V", meta, history, links, expected)["passed"]

    summary = rn.audit_summary("V", meta, history, good, expected)
    assert summary["passed"] and summary["management_checked"] == 1 and summary["audited"] == 1
    assert not passed(good[1:])
    assert not passed([*good[:2], {**good[2], "shared": True}, good[3]])
    failed = rn.audit_summary("V", meta, history, [*good[:2], {**good[2], "engine_state_equal": False}, good[3]], expected)
    assert not failed["passed"] and failed["failures"] == [f"RUN:{START.isoformat()}"]
    assert not passed(meta={**meta, "replay_reproduces_run": False})
    # review RR1: the required links are the base run's; the stored lists cannot shrink them
    assert not passed(meta={**meta, "run_instants": [], "sample": []})
    assert not passed(meta={**meta, "run_instants": expected["run_instants"][:1]})
    assert not passed(meta={**meta, "sample": []})
    assert not passed(meta={key: value for key, value in meta.items() if key != "reproduced"})
    # a base run with no instant proves nothing, though its history links are all there
    assert not passed(good[:2], {**meta, "run_instants": [], "sample": []}, {"run_instants": [], "sample": [], "managed": []})
    # a link missing any check of its kind, or with a management check where none belongs, proves nothing
    for name in ("entry_row_equal", "intent_equal", "composition_equal", "replay_prefix_equal", "engine_state_equal", "management_row_equal"):
        assert not passed([*good[:3], {key: value for key, value in good[3].items() if key != name}]), name
        assert not passed([*good[:3], {**good[3], name: "True"}]), name
    assert not passed([{key: value for key, value in good[0].items() if key != "entry_row_equal"}, *good[1:]])
    assert not passed([*good[:3], {**good[3], "management_row_equal": None}])
    assert not passed([*good[:2], {**good[2], "management_row_equal": True}, good[3]])
    assert not passed([*good[:2], {**good[2], "kind": "OTHER"}, good[3]])


def test_the_audit_expects_management_where_the_composer_managed():
    # review RR1: an open position at an instant without its decision bar is a missing-bar row, never managed
    def row(day, *, intent=None, open_=False, missing=False):
        reasons = [ec.CAUSE_DECISION_PRICE_BAR_MISSING] if missing else ["SOMETHING"]
        return {"decision_at": (START + day * DAY).isoformat(), "intent": intent, "position_open": open_, "reasons": reasons}

    record = {
        "entry_ledger": [row(-1), row(0), row(1, intent={"source_id": "arm"}), row(2, open_=True), row(3, open_=True, missing=True), row(4, open_=True)],
        "management_ledger": [{"decision_at": (START + 2 * DAY).isoformat(), "intent": None}, {"decision_at": (START + 4 * DAY).isoformat(), "intent": {"source_id": "trim"}}],
    }
    context = SimpleNamespace(evaluation={"V": (START, START + 4 * DAY)})
    expected = rn.audit_expectation("V", context, record)
    assert expected["run_instants"] == [(START + day * DAY).isoformat() for day in range(5)]
    assert expected["managed"] == [(START + 2 * DAY).isoformat(), (START + 4 * DAY).isoformat()]
    intents = [instant for instant, reason in expected["sample"] if reason == "INTENT"]
    assert intents == [(START + DAY).isoformat(), (START + 4 * DAY).isoformat()] and len(expected["sample"]) == 5


def test_resumed_audit_files_cannot_drop_the_proof(end_to_end, tmp_path):
    # review RR1: emptied stored instants, or links without their checks, passed and published
    context = end_to_end.context
    base = rn.read_run(end_to_end.workspace.directory, rn.RunSpec(rn.HEADLINE, "BITSTAMP", rn.CHAMPION, "base"), context)
    binding = rn.audit_binding(context, "BITSTAMP", base)
    expected = rn.audit_expectation("BITSTAMP", context, base)
    assert expected["run_instants"] == [(START + DAY * index).isoformat() for index in range((LAST - START) // DAY + 1)]
    assert expected["managed"] and len(expected["sample"]) == len(expected["run_instants"])

    def copied():
        target = tmp_path / f"copy{len(list(tmp_path.iterdir()))}"
        shutil.copytree(end_to_end.workspace.directory, target)
        return rn.Workspace(target)

    def rewritten(path, change):
        data = json.loads(path.read_bytes())
        change(data)
        path.write_bytes(canonical_json_bytes(data))

    control = rn.read_audit(copied(), "BITSTAMP", context, binding)
    assert control["passed"] and control["run_links"] == len(expected["run_instants"]) and control["management_checked"] == len(expected["managed"])
    workspace = copied()
    rewritten(rn.audit_meta_file(workspace, "BITSTAMP"), lambda meta: meta.update(run_instants=[], sample=[]))
    emptied = rn.read_audit(workspace, "BITSTAMP", context, binding)
    assert not emptied["passed"] and not emptied["complete"] and emptied["run_links"] == control["run_links"]
    assert emptied["sample_size"] == control["sample_size"]

    workspace = copied()
    stripped = [(rn.HISTORY_LINK, SCHEDULE[5]), (rn.RUN_LINK, START + 2 * DAY)]
    for kind, instant in stripped:
        rewritten(rn.audit_links_file(workspace, kind, instant), lambda data: data.update(links=[{key: value for key, value in item.items() if not key.endswith("_equal")} for item in data["links"]]))
    failed = rn.read_audit(workspace, "BITSTAMP", context, binding)
    assert not failed["passed"] and failed["failures"] == [f"{kind}:{instant.isoformat()}" for kind, instant in stripped]

    workspace = copied()
    rewritten(rn.audit_links_file(workspace, rn.RUN_LINK, START + 3 * DAY), lambda data: data.update(links=[]))
    assert not rn.read_audit(workspace, "BITSTAMP", context, binding)["passed"]
    for change in (
        lambda data: data.update(links=[{**item, "decision_at": (START + 4 * DAY).isoformat()} for item in data["links"]]),
        lambda data: data.pop("links"),
        lambda data: data.update(links=["not a link"]),
    ):
        workspace = copied()
        rewritten(rn.audit_links_file(workspace, rn.RUN_LINK, START + 3 * DAY), change)
        with pytest.raises(rn.RunnerRefused, match="AUDIT_REFUSED"):
            rn.read_audit(workspace, "BITSTAMP", context, binding)


# --- the report ---------------------------------------------------------------------------------------


def test_the_hold_bands_are_rulebook_20s_at_the_configured_thresholds():
    bands = [rr.hold_band(Decimal(score), CONFIG) for score in ("85", "84.99", "70", "60", "59.9", "50", "49", "40", "39.99")]
    assert bands == ["HOLD_POSSIBLE_ADD", "HOLD", "HOLD", "HOLD_NO_ADD", "DEFENSIVE", "DEFENSIVE", "TRIM", "TRIM", "EXIT"]


def test_the_ablation_band_count_rescores_the_champions_own_inputs(headline, context):
    variant = next(variant for variant in context.registry.variants.values() if variant.role == rn.ABLATION)
    rows = headline.record["management_ledger"]
    counted = rr.ablation_band_differences(rows, CONFIG, variant.config)
    assert counted["hold_evaluations"] == sum(1 for row in rows if row["hold"] and row["hold"]["complete"])
    assert 0 <= counted["differing_action_band"] <= counted["hold_evaluations"]
    assert rr.ablation_band_differences(rows, CONFIG, CONFIG)["differing_action_band"] == 0
    tampered = copy.deepcopy(rows)
    tampered[0]["hold"]["score"] = "1"
    with pytest.raises(rn.RunnerRefused, match="ABLATION_REFUSED"):
        rr.ablation_band_differences(tampered, CONFIG, variant.config)


def test_gap_exposure_counts_lookbacks_that_span_an_omitted_bar():
    gapped = Scenario(start=utc(2024, 1, 1), end=utc(2024, 3, 1), missing_hours=(utc(2024, 2, 5, 10),)).build()
    whole = Scenario(start=utc(2024, 1, 1), end=utc(2024, 3, 1)).build()
    instants = [utc(2024, 2, 3), utc(2024, 2, 7), utc(2024, 2, 12), utc(2024, 2, 13), utc(2024, 2, 28)]
    exposed = rr.gap_exposure(gapped, instants)
    assert rr.gap_exposure(whole, instants)["latest_value"]["realized_volatility_from_daily_bars RV_7"] == 0
    assert exposed["days_before_an_omitted_daily_bar"] == ["2024-02-04"]
    # RV_7 reads 8 daily rows: on 2024-02-13 they still reach 2024-02-04, across the omitted day
    assert exposed["latest_value"]["realized_volatility_from_daily_bars RV_7"] == 3
    assert exposed["latest_value"]["realized_volatility_from_daily_bars RV_60"] == 4
    # the omitted week shows inside the weekly series once a later week exists
    assert exposed["weekly_swing_series"] == 1


def test_exposure_follows_the_rows_each_owner_reads_with_its_history():
    # review F6: the z-score history is 20 observations before the current one, so 4-week momentum reads
    # 29 + 20 = 49 daily rows; the volatility percentile reads RV_20 windows over two years
    assert {owner: rows for owner, _timeframe, _latest, rows in rr.ROW_LOOKBACKS if "momentum" in owner or "weekly" in owner} == {
        "four_week_momentum_from_daily_bars": 49,
        "twelve_week_momentum_from_daily_bars": 105,
        "twenty_week_ma_distance_from_weekly_bars": 40,
        "fifty_two_week_high_distance_from_weekly_bars": 72,
        "price_momentum_from_daily_bars R_7": 8,
    }
    gapped = Scenario(start=utc(2024, 1, 1), end=utc(2024, 4, 10), missing_hours=(utc(2024, 2, 5, 10),)).build()
    # on 2024-03-25 the 49 rows reach back to 2024-02-04, across the omitted 2024-02-05; a day later they do not
    exposed = rr.gap_exposure(gapped, [utc(2024, 3, 25), utc(2024, 3, 26)])
    assert exposed["with_zscore_history"]["four_week_momentum_from_daily_bars"] == 1
    assert exposed["latest_value"]["realized_volatility_from_daily_bars RV_20"] == 0
    assert exposed["volatility_percentile_history"] == 2 and exposed["any_realized_volatility"] == 2
    assert exposed["any_row_owner"] == 2


def test_limitation_exposure_counts_recorded_codes_and_every_composition():
    entry = [
        {"reasons": ["NO_TRADE"], "flags": {"crowding": {"flagged": True}, "stress": {"mapped": None}}, "guard_refusals": [{"guard_id": "OI_GROWTH_ZERO_VARIANCE_GUARD_V1"}], "owner_reason_codes": {"x": {"reason_codes": ["LEVEL_VOLUME_PERCENTILE_WARM_UP"]}}},
        {"reasons": [ec.CAUSE_DECISION_PRICE_BAR_MISSING], "flags": {}, "guard_refusals": []},
    ]
    management = [{"hold": {"score": "70"}, "reasons": ["RULEBOOK_24_NO_ADDING_ENFORCED"], "intent": {"action": "TRAIL"}, "add": {"outcome": "NOT_EVALUATED"}}]
    entry.append({"reasons": ["NO_TRADE"], "flags": {}, "guard_refusals": [{"guard_id": "FUNDING_HEALTH_ZERO_VARIANCE_GUARD_V1"}, {"guard_id": "OI_GROWTH_ZERO_VARIANCE_GUARD_V1"}]})
    gaps = {"latest_value": {"realized_volatility_from_daily_bars RV_7": 0}, "with_zscore_history": {"x": 0}, "weekly_swing_series": 0, "any_row_owner": 3, "any_realized_volatility": 2}
    rows = {row["limitation_id"]: row for row in rr.limitation_exposure(entry, management, gaps)}
    assert rows["SEVERE_CROWDING_IS_CROWDING"]["exposed_instants"] == 1
    assert rows["STRESS_NON_DISCRETIONARY_MISSING"]["exposed_instants"] == 1
    # one instant with both guards' refusals counts once (review F6)
    assert rows["E1_CLASS_FUNDING_AND_OI_GROWTH"]["exposed_instants"] == 2
    assert rows["ROW_BASED_LOOKBACKS"]["exposed_instants"] == 3 and rows["REALIZED_VOLATILITY_GAPPED_SERIES"]["exposed_instants"] == 2
    assert rows["LEVEL_VOLUME_PRE_WARM_UP_PIVOTS"]["exposed_instants"] == 1
    assert rows["RULEBOOK_24_NO_ADDING_ENFORCED"]["exposed_instants"] == 1
    assert rows["ONE_ADD_PER_STRUCTURE"]["exposed_instants"] == 1
    assert rows["REACTION_UNIT"]["exposed_instants"] == 2  # two evaluated rows; the missing-bar row composed nothing
    assert rows["BTC186_FIFTH_CANDIDATE"]["kind"] == "NOT_COMPOSED"


# --- end to end: the orchestration, the resume, the report and the index ------------------------------


@pytest.fixture(scope="module")
def end_to_end(markets, preregistration, tmp_path_factory):
    registry = _registry(preregistration)
    context = rn.RunContext(
        inputs=dict(markets),
        registry=registry,
        evaluation={venue: (START, LAST) for venue in markets},
        golden=GOLDEN,
        fold_bars=SYNTHETIC_FOLD_BARS,
        schedule=SCHEDULE,
        binding={"synthetic": "end_to_end"},
    )
    specs = rn.run_plan(list(markets), registry, GOLDEN)
    workspace = rn.Workspace(tmp_path_factory.mktemp("work"))
    rn.execute_all(context, specs, workspace, workers=4, precompute_venue="BITSTAMP")
    # the synthetic plan's three weekly folds stand for the preregistered folds (ruling 4's comparison)
    synthetic = copy.deepcopy(preregistration)
    for venue in markets:
        synthetic["venues"][venue]["walk_forward"]["folds"] = [
            {"fold_number": number + 1, "test_start": (START + 7 * DAY * number).isoformat(), "test_end": (START + 7 * DAY * number + 6 * DAY).isoformat()}
            for number in range(3)
        ]

    def build(substituted=None):
        records = {spec.run_id: rn.read_run(workspace.directory, spec, context) for spec in specs}
        records.update(substituted or {})
        audits = {
            venue: rn.read_audit(workspace, venue, context, rn.audit_binding(context, venue, records[f"HEADLINE:{venue}:champion:base"]))
            for venue in markets
        }
        instants = [instant for instant in SCHEDULE if START <= instant <= LAST]
        gaps = {venue: rr.gap_exposure(markets[venue], instants) for venue in markets}
        return rr.build_report(
            preregistration=synthetic,
            preregistration_sha256="synthetic",
            identity={"synthetic": True},
            context=context,
            specs=specs,
            records=records,
            audits=audits,
            gaps=gaps,
            sweep_specs=rn.sweep_specs(preregistration["threshold_sweeps"]["sweeps"], CONFIG)[:1],
            coverage_index={},
        )

    report, files = build()
    return SimpleNamespace(context=context, specs=specs, workspace=workspace, report=report, files=files, build=build)


def test_the_report_states_the_evidence_class_first(end_to_end):
    report = end_to_end.report
    assert next(iter(report)) == "evidence"
    evidence = report["evidence"]
    assert evidence["evidence_class"] == "RESEARCH_BACKTEST_NON_CERTIFYING" and evidence["canonical_reference"] == "UNRESOLVED"
    assert len(evidence["prohibited_uses"]) == 5 and evidence["holdout"] == "NOT COLLECTED"
    assert set(evidence["named_limitations"]) == {"BITSTAMP", "COINBASE"}
    assert report["identity"]["report_version"] == "RESEARCH_BACKTEST_REPORT_V1" == rn.prereg.REPORT_VERSION
    assert report["identity"]["report_artifact_version"] == rr.REPORT_ARTIFACT_VERSION
    # review F10: in the files as written, not only in the dictionary
    written = end_to_end.files[rr.REPORT_FILE]
    assert written.startswith(b'[["evidence",{') and json.loads(written)[0] == ["evidence", json.loads(canonical_json_bytes(evidence))]
    assert [name for name, _section in json.loads(written)] == list(report)
    markdown = end_to_end.files[rr.REPORT_MARKDOWN_FILE].decode().splitlines()
    first_metric = next(index for index, line in enumerate(markdown) if line.startswith("## Headline"))
    opening = "\n".join(markdown[:first_metric])
    assert "RESEARCH_BACKTEST_NON_CERTIFYING" in opening and "Prohibited uses:" in opening and "## Named limitations" in opening
    assert all(row["limitation_id"] in opening for rows in evidence["named_limitations"].values() for row in rows)
    with pytest.raises(rn.RunnerRefused, match="REPORT_REFUSED"):
        rr.report_bytes({"identity": {}, **report})


def test_every_run_has_a_record_and_the_checks_pass(end_to_end):
    integrity = end_to_end.report["integrity"]
    assert integrity["runs"] == integrity["planned_runs"] == len(end_to_end.specs) == 2 * 10
    assert all(integrity["memory_matches_history"].values())
    assert integrity["unaccounted"] == {}
    # owner ruling 8: every record counts its engine results the rule accepted; the synthetic runs need none
    assert integrity["engine_rounding"] == {}
    records = [rn.read_run(end_to_end.workspace.directory, spec, end_to_end.context) for spec in end_to_end.specs]
    assert all(record["engine_rounding"] == {"fees": 0, "funding": 0} for record in records)
    markdown = end_to_end.files[rr.REPORT_MARKDOWN_FILE].decode()
    assert "## The engine's fee and funding checks (owner ruling 8)" in markdown and "- 0 of 20 runs had an engine result" in markdown
    # owner ruling 9: every walk-forward record counts its report rows the rule accepted; the synthetic runs need none
    assert integrity["report_rounding"] == {}
    walk_forward = [record for spec, record in zip(end_to_end.specs, records, strict=True) if spec.kind == rn.WALK_FORWARD]
    assert walk_forward and all(record["report_rounding"] == {"bucket_pnl": 0, "setup_pnl": 0, "setup_costs": 0} for record in walk_forward)
    assert all("report_rounding" not in record for spec, record in zip(end_to_end.specs, records, strict=True) if spec.kind != rn.WALK_FORWARD)
    assert "## The regime and setup reports' row checks (owner ruling 9)" in markdown and "- 0 of 20 runs had a report row" in markdown
    for audit in end_to_end.report["lookahead_audit"].values():
        assert audit["passed"] and audit["complete"] and audit["failures"] == []
        assert audit["history_links"] == len(SCHEDULE) and audit["run_links"] == (LAST - START) // DAY + 1
        assert audit["audited"] == audit["sample_size"] > rn.AUDIT_SEEDED_INSTANTS and audit["management_checked"] > 0


def test_every_rate_has_its_trade_count(end_to_end):
    report = end_to_end.report
    for rungs in report["headline"].values():
        for entry in rungs.values():
            for name, metric in entry["metrics"].items():
                assert any(key in metric for key in ("closed_trades", "trades")), name
    # review F9: the dispersion and the summary's per-fold rates keep theirs too
    for rows in report["cross_venue"]["metric_dispersion"].values():
        for name, row in rows.items():
            assert set(row["counts"]) == {"BITSTAMP", "COINBASE"}
            assert all(any(key in counts for key in ("closed_trades", "trades")) for counts in row["counts"].values()), name
    markdown = end_to_end.files[rr.REPORT_MARKDOWN_FILE].decode()
    folds = [line for line in markdown.splitlines() if "calmar per fold" in line]
    assert len(folds) == 2 and all(line.count("(n=") == 3 for line in folds)


def test_the_sweeps_and_the_ablation_are_labelled_sensitivity_only(end_to_end):
    report = end_to_end.report
    for venue in ("BITSTAMP", "COINBASE"):
        assert report["ablation"][venue]["label"] == "SENSITIVITY_ONLY_NOT_SELECTION"
        sweep = report["sweeps"][venue][0]
        assert sweep["label"] == "SENSITIVITY_ONLY_NOT_SELECTION" and len(sweep["candidates"]) == 2
        assert all("validation" not in point for point in sweep["report"]["points"])


def test_the_golden_replay_reports_its_decisions_beside_the_scripted_ones(end_to_end):
    golden = end_to_end.report["golden_replays"]["synthetic_golden"]["BITSTAMP"]
    assert not golden["engine_refused"]
    # review F13: the golden runs count the engine's events as every other run does
    assert golden["engine_events"] and all(key.count(":") >= 2 for key in golden["engine_events"])
    assert all("engine_events" in record for spec, record in ((spec, rn.read_run(end_to_end.workspace.directory, spec, end_to_end.context)) for spec in end_to_end.specs))
    assert golden["decisions_beside_scripted"][0]["scripted_action"] == "ARM_ENTRY"
    assert golden["decisions_beside_scripted"][0]["decision_at"] == "2024-03-31T00:00:00+00:00"


def test_a_resumed_run_runs_every_run_again_and_reproduces_the_report(end_to_end, monkeypatch, tmp_path):
    files = [path(end_to_end.workspace.directory, spec) for spec in end_to_end.specs for path in (rn.run_file, rn.run_snapshot_file)]
    before = {path: path.read_bytes() for path in files}
    logged = len(end_to_end.workspace.log.read_text().splitlines())
    calls = tmp_path / "executed"
    execute = rn.execute_run

    def executed(spec, context, **options):
        # the workers are forked from this process, so each one runs this and appends its own line
        with calls.open("a") as stream:
            stream.write(spec.run_id + "\n")
        return execute(spec, context, **options)

    monkeypatch.setattr(rn, "execute_run", executed)
    rn.execute_all(end_to_end.context, end_to_end.specs, end_to_end.workspace, workers=2, precompute_venue="BITSTAMP")
    after = {path: path.read_bytes() for path in files}
    assert before == after
    # review T2: every written run was run again, once, and found to be the stored run, which stays as written
    assert sorted(calls.read_text().split()) == sorted(spec.run_id for spec in end_to_end.specs)
    entries = [json.loads(line) for line in end_to_end.workspace.log.read_text().splitlines()[logged:]]
    runs = [entry for entry in entries if entry["event"] == "run"]
    assert sorted(entry["run_id"] for entry in runs) == sorted(spec.run_id for spec in end_to_end.specs)
    assert all(entry["resumed"] is True for entry in runs)
    # with the stored shared positioning results: nothing shared was computed again
    assert all(counts["computed"] == 0 for entry in runs for counts in entry["share"].values())
    assert sum(counts["served"] for entry in runs for counts in entry["share"].values()) > 0
    _report, files = end_to_end.build()
    assert files == end_to_end.files


def test_an_audit_file_from_another_binding_or_missing_refuses(end_to_end, tmp_path):
    context = end_to_end.context
    base = rn.read_run(end_to_end.workspace.directory, rn.RunSpec(rn.HEADLINE, "BITSTAMP", rn.CHAMPION, "base"), context)
    binding = rn.audit_binding(context, "BITSTAMP", base)

    def copied():
        target = tmp_path / f"copy{len(list(tmp_path.iterdir()))}"
        shutil.copytree(end_to_end.workspace.directory, target)
        return rn.Workspace(target)

    assert rn.read_audit(copied(), "BITSTAMP", context, binding)["passed"]
    with pytest.raises(rn.RunnerRefused, match="AUDIT_REFUSED"):
        rn.read_audit(copied(), "BITSTAMP", context, {**binding, "base_run_record_sha256": "0" * 64})
    workspace = copied()
    path = rn.audit_links_file(workspace, rn.HISTORY_LINK, SCHEDULE[5])
    data = json.loads(path.read_bytes())
    data["binding"]["context"] = {"foreign": True}
    path.write_bytes(canonical_json_bytes(data))
    with pytest.raises(rn.RunnerRefused, match="AUDIT_REFUSED"):
        rn.read_audit(workspace, "BITSTAMP", context, binding)
    workspace = copied()
    rn.audit_links_file(workspace, rn.RUN_LINK, START + 2 * DAY).unlink()
    with pytest.raises(rn.RunnerRefused, match="AUDIT_REFUSED"):
        rn.read_audit(workspace, "BITSTAMP", context, binding)
    workspace = copied()
    rn.audit_state_file(workspace, "BITSTAMP").write_bytes(pickle.dumps({"binding": {"foreign": True}, "state": None}))
    with pytest.raises(rn.RunnerRefused, match="AUDIT_REFUSED"):
        rn.load_audit_state(workspace, "BITSTAMP", binding)


def test_a_failed_required_check_publishes_nothing(end_to_end, tmp_path):
    # review F4: failures were recorded, but every output was still written and the command succeeded
    report, files = end_to_end.report, end_to_end.files
    assert rr.publication_refusals(report) == []
    workspace = rn.Workspace(tmp_path / "work")
    rn.publish(report, files, private=tmp_path / "private", public=tmp_path / "public", workspace=workspace)
    assert sorted(path.name for path in (tmp_path / "private").iterdir()) == sorted(files)
    assert [path.name for path in (tmp_path / "public").iterdir()] == [rr.INDEX_FILE]

    def broken(change):
        copy_ = copy.deepcopy(report)
        change(copy_)
        return copy_

    venue = "BITSTAMP"
    cases = {
        "LOOKAHEAD_AUDIT_FAILED:BITSTAMP": lambda r: r["lookahead_audit"][venue].update(passed=False),
        "MEMORY_MISMATCH:HEADLINE:BITSTAMP:champion:base": lambda r: r["integrity"]["memory_matches_history"].update({"HEADLINE:BITSTAMP:champion:base": False}),
        "UNACCOUNTED_CAUSES:SWEEP:x": lambda r: r["integrity"]["unaccounted"].update({"SWEEP:x": ["entry:BITSTAMP:CODE"]}),
        "FOLD_DATES_INCONSISTENT:BITSTAMP": lambda r: r["walk_forward"][venue]["ruling_4"].update(consistent=False),
        "GOLDEN_ENGINE_REFUSED:synthetic_golden:BITSTAMP": lambda r: r["golden_replays"]["synthetic_golden"][venue].update(engine_refused=True),
        "RUNS_INCOMPLETE": lambda r: r["integrity"].update(runs=r["integrity"]["runs"] - 1),
    }
    for number, (refusal, change) in enumerate(cases.items()):
        failing = broken(change)
        assert rr.publication_refusals(failing) == [refusal]
        work = rn.Workspace(tmp_path / f"work{number}")
        with pytest.raises(rn.RunnerRefused, match="PUBLICATION_REFUSED"):
            rn.publish(failing, files, private=tmp_path / f"private{number}", public=tmp_path / f"public{number}", workspace=work)
        assert not (tmp_path / f"private{number}").exists() and not (tmp_path / f"public{number}").exists()
        assert json.loads((work.directory / rn.REFUSED_REPORT_FILE).read_bytes())["refusals"] == [refusal]


def _injected_golden(monkeypatch, context, where):
    """A synthetic golden run whose composers record one unaccounted cause, as a real row or follow-up holds it."""

    from btc_predictor.research_backtest import management_composer as mc

    class Entry(rn.RegisteredEntryComposer):
        def decide(self, as_of, *, position_open=False):
            decision = super().decide(as_of, position_open=position_open)
            if where == "entry" and as_of == utc(2024, 3, 31):
                self._ledger[-1] = replace(self._ledger[-1], unaccounted=("INJECTED_ENTRY",))
            return decision

    class Management(mc.ManagementComposer):
        def record(self, decision):
            super().record(decision)
            if where == "management" and not any(row.unaccounted for row in self._ledger):
                self._ledger[-1] = replace(self._ledger[-1], unaccounted=("INJECTED_MANAGEMENT",))
            if where == "followup" and not self._followups:
                self._followups.append(mc.AddFollowUp(decision.row.decision_at, decision.row.decision_at, "INJECTED", (), None, None, ("INJECTED_FOLLOWUP",)))

    monkeypatch.setattr(rn, "RegisteredEntryComposer", Entry)
    monkeypatch.setattr(rn, "ManagementComposer", Management)
    spec = rn.RunSpec(rn.GOLDEN, "BITSTAMP", rn.CHAMPION, "base", "synthetic_golden")
    outcome = rn.execute_run(spec, context)
    monkeypatch.undo()
    return spec, outcome


def test_a_golden_runs_unaccounted_cause_refuses_publication(end_to_end, monkeypatch, tmp_path):
    # review RR4: golden records carried no causes, and the report read their absence as none
    context = end_to_end.context
    spec = rn.RunSpec(rn.GOLDEN, "BITSTAMP", rn.CHAMPION, "base", "synthetic_golden")
    assert rn.read_run(end_to_end.workspace.directory, spec, context)["unaccounted"] == []
    for where, label in (("entry", "entry:"), ("management", "management:"), ("followup", "management:")):
        spec, outcome = _injected_golden(monkeypatch, context, where)
        causes = outcome.record["unaccounted"]
        assert len(causes) == 1 and causes[0].startswith(label) and causes[0].endswith(f"INJECTED_{where.upper()}"), causes
        report, files = end_to_end.build({spec.run_id: outcome.record})
        assert report["integrity"]["unaccounted"] == {spec.run_id: causes}
        assert rr.publication_refusals(report) == [f"UNACCOUNTED_CAUSES:{spec.run_id}"]
        with pytest.raises(rn.RunnerRefused, match="PUBLICATION_REFUSED"):
            rn.publish(report, files, private=tmp_path / f"private-{where}", public=tmp_path / f"public-{where}", workspace=rn.Workspace(tmp_path / f"work-{where}"))
        assert not (tmp_path / f"private-{where}").exists() and not (tmp_path / f"public-{where}").exists()
    # a golden record without the field is not read as one without causes
    stored = rn.read_run(end_to_end.workspace.directory, spec, context)
    path = rn.run_file(tmp_path / "work", spec)
    path.parent.mkdir(parents=True)
    path.write_bytes(gzip.compress(canonical_json_bytes({key: value for key, value in stored.items() if key != "unaccounted"})))
    with pytest.raises(rn.RunnerRefused, match="CHECKPOINT_REFUSED"):
        rn.read_run(tmp_path / "work", spec, context)
    with pytest.raises(KeyError):
        end_to_end.build({spec.run_id: {key: value for key, value in stored.items() if key != "unaccounted"}})


def test_the_public_index_is_value_free(end_to_end):
    index = rr.public_index(end_to_end.report, end_to_end.files, private_commit=None)
    text = canonical_json_bytes(index).decode()
    for word in ("metrics", "trades", "nav", "pnl", "price", "equity", "score"):
        assert f'"{word}' not in text
    assert set(index["files"]) == set(end_to_end.files)
    assert index["memory_check_failures"] == 0 and index["runs"] == 20
    assert index["runs_with_engine_rounding_accepted"] == 0
    assert index["runs_with_report_rounding_accepted"] == 0


def test_engine_rounding_is_counted_in_the_report_and_the_index(end_to_end):
    # owner ruling 8: a run whose engine results the rule accepted is listed and counted, value-free
    spec = end_to_end.specs[0]
    stored = rn.read_run(end_to_end.workspace.directory, spec, end_to_end.context)
    report, files = end_to_end.build({spec.run_id: {**stored, "engine_rounding": {"fees": 2, "funding": 1}}})
    assert report["integrity"]["engine_rounding"] == {spec.run_id: {"fees": 2, "funding": 1}}
    assert rr.publication_refusals(report) == []
    index = rr.public_index(report, files, private_commit=None)
    assert index["runs_with_engine_rounding_accepted"] == 1
    markdown = files[rr.REPORT_MARKDOWN_FILE].decode()
    assert "- 1 of 20 runs had an engine result whose account total differed from its trades' total" in markdown
    assert "fees in 2 and funding in 1 engine results." in markdown


def test_report_rounding_is_counted_in_the_report_and_the_index(end_to_end):
    # owner ruling 9: a walk-forward run whose report rows the rule accepted is listed and counted, value-free
    spec = next(spec for spec in end_to_end.specs if spec.kind == rn.WALK_FORWARD)
    stored = rn.read_run(end_to_end.workspace.directory, spec, end_to_end.context)
    counts = {"bucket_pnl": 3, "setup_pnl": 1, "setup_costs": 2}
    report, files = end_to_end.build({spec.run_id: {**stored, "report_rounding": counts}})
    assert report["integrity"]["report_rounding"] == {spec.run_id: counts}
    assert rr.publication_refusals(report) == []
    index = rr.public_index(report, files, private_commit=None)
    assert index["runs_with_report_rounding_accepted"] == 1 and index["runs_with_engine_rounding_accepted"] == 0
    markdown = files[rr.REPORT_MARKDOWN_FILE].decode()
    assert "- 1 of 20 runs had a report row whose total differed from the sum of its parts" in markdown
    assert "bucket P&L in 3, setup P&L in 1 and setup costs in 2 rows." in markdown


def test_the_decision_ledgers_are_the_champions_base_run(end_to_end):
    ledger = json.loads(end_to_end.files[rr.ledger_file("BITSTAMP")])
    assert ledger["run"]["kind"] == rn.HEADLINE and ledger["run"]["cost_rung"] == "base"
    assert ledger["entry_rows"][0]["decision_at"] == START.isoformat()


def test_main_refuses_when_the_code_is_not_frozen(monkeypatch, tmp_path):
    from btc_predictor.research_backtest import dataset_build as build

    monkeypatch.setattr(build, "code_commit", lambda repository=None: "0" * 40)

    def refused(repository, commit):
        raise rn.RunnerRefused("FROZEN_CODE_REFUSED", "test")

    monkeypatch.setattr(rn, "require_frozen_code", refused)
    monkeypatch.setattr(rn, "fresh_bytecode_process", lambda: True)
    monkeypatch.setattr(rn, "require_fresh_bytecode", lambda: str(tmp_path))  # review Q1: main's first check
    lines = []
    assert rn.main(["run", "--store", str(tmp_path)], out=lines.append) == 2
    assert lines == ["refused: FROZEN_CODE_REFUSED: test"]
    assert not (REPOSITORY / rn.prereg.ARTIFACT_DIRECTORY / rr.INDEX_FILE).exists()
