# Quantitative Core Policy

Policy version: `FLOAT64_V1`.

## Numeric Representation

- Internal arrays use NumPy `float64` exclusively.
- Public boundaries return owned, C-contiguous arrays and never mutate inputs.
- Decimal conversion, persistence formatting, and domain reason codes stay
  outside `btc_predictor.quant`.
- Complex and boolean arrays are rejected instead of being silently coerced.

## Shapes

- Vector helpers require exactly one dimension; matrix helpers require exactly
  two dimensions.
- Empty arrays are rejected unless a boundary explicitly opts in.
- Elementwise operations require identical shapes. Implicit NumPy broadcasting
  is not part of the public contract.
- Portfolio matrices use rows as observations and columns as assets.

## NaN And Infinity

- Infinity is rejected at every public boundary.
- NaN is rejected by default.
- `propagate` must be requested explicitly and produces NaN where an input or
  rolling window is incomplete.
- `omit` is reserved for reduction helpers whose behavior will be implemented
  and parity-tested in BTC-043. BTC-042 boundaries support only `raise` and
  `propagate`; they never silently remove observations.
- Rolling warm-up periods are represented by NaN, not zero.

## Tolerances And Statistics

- Default absolute and relative comparison tolerances are both `1e-12`.
- Near-zero denominators and effectively constant z-score inputs fail.
- Degrees of freedom are explicit and default to population statistics
  (`ddof=0`).
- Quantiles use NumPy's deterministic `linear` interpolation method.
- Percentile ranks use the mean rank for ties.
- Return transforms emit `n-1` observations and do not invent a padded first
  return.

## Determinism And Boundaries

- Simulation requires an explicit non-negative seed and uses NumPy `PCG64`.
- Helpers do not access clocks, global random state, files, networks, databases,
  configuration, trading actions, or mutable application state.
- The package may depend on the Python standard library, NumPy, SciPy, and other
  modules within `btc_predictor.quant` only.
