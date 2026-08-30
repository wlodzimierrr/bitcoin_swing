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
- Raw array boundaries support only `raise` and `propagate`; they never silently
  remove observations.
- BTC-043 rolling reductions additionally support `omit`, count only finite
  values toward `min_periods`, and retain the original output shape. Temporal
  returns and true range do not support omission because it would change
  observation adjacency.
- Rolling warm-up periods are represented by NaN, not zero.

## Tolerances And Statistics

- Default absolute and relative comparison tolerances are both `1e-12`.
- BTC-043 parity against the BTC-041 Decimal oracle uses absolute and relative
  tolerances of `1e-12`.
- Near-zero denominators and effectively constant z-score inputs fail.
- Degrees of freedom are explicit and default to population statistics
  (`ddof=0`).
- Quantiles use NumPy's deterministic `linear` interpolation method.
- Percentile ranks use the mean rank for ties.
- Return transforms emit `n-1` observations and do not invent a padded first
  return.

## Rolling Windows

- Mean, volatility, true range, ATR, and realized volatility include the
  current completed observation.
- Z-scores, percentile ranks, and historical normalization compare the current
  observation only with prior history.
- Realized volatility uses population standard deviation by default and
  annualizes simple close-to-close returns by `sqrt(annualization_periods)`.
- Warm-up and undefined results remain NaN in the NumPy layer and convert to
  `None` only at existing Decimal-facing feature boundaries.
- Appending future observations cannot change an earlier result.

## Nonlinear Transforms

- Elementwise transforms accept scalar or array-like input. Scalar input
  returns a Python `float`; array-like input returns an owned, shape-preserving
  `float64` array.
- Score and percentile ranges are explicit. Degenerate intervals, zero-width
  distributions, invalid probabilities, and negative decay distances fail
  before calculation.
- Gaussian health uses `maximum * exp(-0.5 * ((x - preferred) / width)^2)`.
  Normal-CDF scores use SciPy's stable standard-normal primitive and explicit
  output bounds.
- Smooth penalties use a bounded cubic smoothstep transition. Winsorization
  uses deterministic linear-interpolation quantiles across the complete input
  array.
- Under explicit NaN propagation, elementwise transforms preserve NaN at the
  affected locations. A NaN makes the complete winsorized output NaN because
  every output depends on the globally derived quantile bounds.
- Transform helpers contain no strategy interpretation, reason codes,
  persistence behavior, or action decisions.

## Determinism And Boundaries

- Simulation requires an explicit non-negative seed and uses NumPy `PCG64`.
- Helpers do not access clocks, global random state, files, networks, databases,
  configuration, trading actions, or mutable application state.
- The package may depend on the Python standard library, NumPy, SciPy, and other
  modules within `btc_predictor.quant` only.
