import ast
import inspect
import tomllib
from pathlib import Path

import numpy as np
import pytest
import scipy
from scipy import stats

import btc_predictor.quant as quant
from btc_predictor.quant import (
    FLOAT_DTYPE,
    QUANT_POLICY_VERSION,
    NumericInputError,
    NumericTolerance,
    as_float64_array,
    as_float64_matrix,
    as_float64_vector,
    is_effectively_zero,
    normal_samples,
    require_probability,
    require_same_shape,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
QUANT_ROOT = REPOSITORY_ROOT / "btc_predictor/quant"
EXPECTED_MODULES = {
    "arrays.py",
    "distances.py",
    "portfolio.py",
    "risk.py",
    "rolling.py",
    "scoring.py",
    "simulation.py",
    "statistics.py",
    "transforms.py",
}


def test_numpy_and_scipy_are_core_runtime_dependencies() -> None:
    project = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text())
    dependencies = project["project"]["dependencies"]

    assert any(item.startswith("numpy>=") for item in dependencies)
    assert any(item.startswith("scipy>=") for item in dependencies)
    assert np.__version__
    assert scipy.__version__
    assert stats.norm.cdf(0) == pytest.approx(0.5)


def test_quant_package_contains_frozen_initial_module_set() -> None:
    assert EXPECTED_MODULES <= {path.name for path in QUANT_ROOT.glob("*.py")}
    assert QUANT_POLICY_VERSION == "FLOAT64_V1"
    assert FLOAT_DTYPE == np.dtype(np.float64)


def test_quant_package_has_no_application_or_database_imports() -> None:
    violations = []
    for path in sorted(QUANT_ROOT.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            imported = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module]
            for module in imported:
                if module.startswith("btc_predictor") and not module.startswith(
                    "btc_predictor.quant"
                ):
                    violations.append(f"{path.name}: {module}")
                if module.startswith(("sqlalchemy", "alembic", "psycopg")):
                    violations.append(f"{path.name}: {module}")

    assert violations == []


def test_adjacent_ticket_namespaces_do_not_preempt_their_implementations() -> None:
    for module_name in (
        "portfolio",
        "risk",
        "scoring",
        "statistics",
    ):
        module = __import__(f"btc_predictor.quant.{module_name}", fromlist=[module_name])
        public_functions = [
            value
            for name, value in vars(module).items()
            if not name.startswith("_") and inspect.isfunction(value)
        ]
        assert public_functions == []


def test_public_quant_helpers_are_fully_annotated() -> None:
    for name in quant.__all__:
        value = getattr(quant, name)
        if not inspect.isfunction(value):
            continue
        signature = inspect.signature(value)
        assert signature.return_annotation is not inspect.Signature.empty, name
        assert all(
            parameter.annotation is not inspect.Signature.empty
            for parameter in signature.parameters.values()
        ), name


def test_float64_coercion_returns_owned_contiguous_array_without_mutating_input() -> None:
    source = np.asarray([1, 2, 3], dtype=np.int64)

    result = as_float64_array(source)
    result[0] = 99

    assert result.dtype == np.float64
    assert result.flags.c_contiguous
    assert result.flags.owndata
    assert source.tolist() == [1, 2, 3]


@pytest.mark.parametrize(
    "values,match",
    [
        ([np.nan], "NaN"),
        ([np.inf], "infinite"),
        ([1 + 2j], "complex"),
        ([True, False], "boolean"),
        (["1", "2"], "string"),
        ([[1, 2], [3]], "regular numeric array"),
    ],
)
def test_invalid_array_inputs_fail_fast(values, match) -> None:
    with pytest.raises(NumericInputError, match=match):
        as_float64_array(values)


def test_nan_requires_explicit_propagation_and_infinity_never_propagates() -> None:
    propagated = as_float64_vector([1, np.nan], nan_policy="propagate")

    assert propagated.dtype == np.float64
    assert np.isnan(propagated[1])
    with pytest.raises(NumericInputError, match="infinite"):
        as_float64_vector([1, np.inf], nan_policy="propagate")
    with pytest.raises(NumericInputError, match="nan_policy"):
        as_float64_vector([1], nan_policy="omit")


def test_shape_policy_rejects_scalars_wrong_dimensions_and_broadcasting() -> None:
    with pytest.raises(NumericInputError, match="one observation"):
        as_float64_vector([])
    with pytest.raises(NumericInputError, match="1 dimensions"):
        as_float64_vector([[1, 2]])
    with pytest.raises(NumericInputError, match="2 dimensions"):
        as_float64_matrix([1, 2])
    with pytest.raises(NumericInputError, match="identical shapes"):
        require_same_shape(as_float64_vector([1, 2]), as_float64_vector([1]))


def test_exact_shape_validation_is_deterministic() -> None:
    first = as_float64_matrix([[1, 2], [3, 4]])
    second = as_float64_matrix([[5, 6], [7, 8]])

    assert require_same_shape(first, second) == (2, 2)
    np.testing.assert_array_equal(first, as_float64_matrix([[1, 2], [3, 4]]))


@pytest.mark.parametrize(
    "tolerance",
    [
        NumericTolerance(absolute=0, relative=0),
        NumericTolerance(absolute=1e-9, relative=1e-6),
    ],
)
def test_numeric_tolerance_accepts_finite_non_negative_values(tolerance) -> None:
    assert tolerance.absolute >= 0
    assert tolerance.relative >= 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"absolute": -1},
        {"relative": np.inf},
        {"absolute": True},
    ],
)
def test_numeric_tolerance_rejects_invalid_values(kwargs) -> None:
    with pytest.raises(NumericInputError, match="tolerance"):
        NumericTolerance(**kwargs)


def test_effective_zero_uses_explicit_tolerance() -> None:
    mask = is_effectively_zero(
        [0, 5e-7, 2e-6],
        tolerance=NumericTolerance(absolute=1e-6, relative=0),
    )

    np.testing.assert_array_equal(mask, [True, True, False])


@pytest.mark.parametrize("value", [-0.1, 1.1, np.nan, np.inf, True])
def test_probability_validation_rejects_invalid_values(value) -> None:
    with pytest.raises(NumericInputError, match="probability"):
        require_probability(value)


def test_probability_validation_returns_float64() -> None:
    result = require_probability(0.95)

    assert result == np.float64(0.95)
    assert isinstance(result, np.float64)


def test_seeded_simulation_is_repeatable_and_does_not_use_global_rng() -> None:
    np.random.seed(999)
    first = normal_samples((2, 3), seed=42)
    np.random.seed(1)
    second = normal_samples((2, 3), seed=42)

    np.testing.assert_array_equal(first, second)
    assert first.shape == (2, 3)
    assert first.dtype == np.float64


@pytest.mark.parametrize("shape,seed", [((2, 0), 1), ((), 1), ((2, 2), -1), (True, 1)])
def test_simulation_requires_positive_shape_and_explicit_non_negative_seed(shape, seed) -> None:
    with pytest.raises(NumericInputError):
        normal_samples(shape, seed=seed)


def test_simulation_rejects_non_finite_parameters() -> None:
    with pytest.raises(NumericInputError, match="finite"):
        normal_samples(2, seed=1, mean=np.nan)
    with pytest.raises(NumericInputError, match="non-negative"):
        normal_samples(2, seed=1, standard_deviation=-1)
    with pytest.raises(NumericInputError, match="boolean"):
        normal_samples(2, seed=1, standard_deviation=True)
    with pytest.raises(NumericInputError, match="float64"):
        normal_samples(2, seed=1, mean="not-a-number")


def test_numeric_policy_documents_required_conventions_and_future_omit_scope() -> None:
    policy = (QUANT_ROOT / "POLICY.md").read_text()

    for requirement in (
        "float64",
        "Infinity",
        "NaN",
        "broadcasting",
        "1e-12",
        "PCG64",
        "databases",
        "BTC-043",
    ):
        assert requirement in policy
