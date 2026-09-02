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
- Portfolio matrices use rows as observations and columns as assets. Aggregate
  portfolio and risk helpers return one result per row and never flatten time
  and asset axes together.

## NaN And Infinity

- Infinity is rejected at every public input boundary and after public
  arithmetic. Finite inputs that exceed the float64 output range fail with
  `NumericInputError` instead of returning infinity.
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
- Arithmetic that is mathematically defined but not representable in `float64`
  raises `NumericInputError`. Numerically stable formulations may use wider
  intermediates, but public numeric outputs remain `float64`.
- NumPy warning handling is scoped to the operation being checked. Runtime
  warnings are never disabled globally, and post-arithmetic validation remains
  mandatory after a locally handled overflow or invalid operation.

## Tolerances And Statistics

- `PARITY_TOLERANCE` centrally owns the default absolute and relative
  comparison tolerances; both are `1e-12`.
- BTC-043/BTC-049 parity against Python and Decimal oracles uses that same
  central tolerance object.
- Near-zero denominators and effectively constant z-score inputs fail.
- Degrees of freedom are explicit and default to population statistics
  (`ddof=0`).
- Quantiles use NumPy's deterministic `linear` interpolation method.
- Percentile ranks use the mean rank for ties.
- Return transforms emit `n-1` observations and do not invent a padded first
  return.

## Hard-Decision Comparisons

- Policy version `DECISION_COMPARISON_V1` governs comparisons between migrated
  `float64` results and Decimal-facing strategy thresholds.
- The comparison band uses the central `PARITY_TOLERANCE`: two values are
  equivalent when their absolute difference is no greater than the larger of
  `1e-12` and `1e-12 * max(abs(left), abs(right))`.
- Inclusive `>=` and `<=` comparisons accept values in the equivalence band.
  Strict `>` and `<` comparisons reject values in that band. Values outside the
  band retain their ordinary ordering.
- Domain decisions use `btc_predictor.quant.comparisons`; compatibility
  wrappers may preserve existing Decimal return types, but binary float text is
  not treated as an authoritative exact threshold boundary.
- This policy is for hard decisions, not for hiding material parity failures or
  changing persisted numeric values through arbitrary rounding.

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

## Price Distances

- Elementwise distance helpers permit explicit scalar expansion against an
  array. Two non-scalar inputs must have identical shapes.
- Prices and finite ATR observations must be strictly positive. ATR-normalized
  operations require ATR explicitly and never substitute zero or a default.
- Directional support and resistance lookups return NaN when no qualifying
  level exists. A propagated NaN in the level set makes all dependent nearest-
  level results NaN.
- Cluster matrices are symmetric with a zero diagonal. `static` is an alias
  for absolute price-unit distance; fractional distance divides by the lower
  pair price, matching BTC-095's sorted-adjacent compatibility formula; ATR
  distance divides by one explicit as-of ATR.
- Entry-distance scores use directional long-entry distance above support.
  Fractional mode divides by entry price to preserve the existing Structure
  Score formula, while ATR mode expresses full-score and no-chase thresholds
  directly in ATR units.

## Weighted Scores

- Weighted scoring accepts one named component row or a two-dimensional
  observation matrix and computes contributions and scores from the same
  `float64` multiplication-and-reduction path.
- Mapping weights are reordered to an explicit component-name sequence and
  must match it exactly. Array weights require component names and exact shape
  alignment.
- Weights are finite, non-negative, and have a positive total. Callers may
  enforce a configured expected total with an explicit absolute tolerance or
  opt out when a domain policy only requires a positive total.
- Missing component inputs are represented by NaN contribution masks. A row
  with any missing component has a NaN score and a false completeness mask;
  missing values are never replaced with zero.
- Domain model selection, score interpretation, reason codes, Decimal scale,
  and persistence formatting remain outside the quantitative layer.

## Risk And Portfolio Mathematics

- Position sides are explicit `long` or `short` values. Quantities and
  notionals are unsigned and non-negative; direction is never inferred from a
  negative quantity.
- Long stop risk is `notional * max((entry - stop) / entry, 0)`. Short stop
  risk is the symmetric `notional * max((stop - entry) / entry, 0)`.
  Profitable stop outcomes therefore contribute zero downside risk, and all
  risk outputs remain non-negative.
- Reward/risk is directional and returns NaN when either the risk leg or reward
  leg is not strictly positive. Maximum-notional sizing rejects zero stop
  distance rather than producing unbounded exposure.
- Realized and unrealized P&L are signed: positive is profitable and negative
  is a loss for the explicitly selected side.
- Gross exposure sums unsigned notionals. Net exposure applies `+1` to long
  notionals and `-1` to short notionals before summing. Portfolio reductions
  use stable summation so small residual exposure is retained when large long
  and short notionals nearly cancel.
- Risk improvement compares aggregate current and proposed portfolio risk
  before flooring the result at zero. Per-tranche clipping must not hide a net
  increase in total risk.
- Empty aggregate portfolios have zero risk and exposure. Weighted-average
  entry is NaN for an empty or zero-total-quantity position because no entry
  price is mathematically defined.
- Risk and portfolio kernels contain no recommendation-action or lifecycle
  decisions and can be shared by advisory, paper-trading, and backtest layers.

## Validation Gate

- `test_quant_validation_gate.py` is the BTC-049 cross-module release gate. It
  covers Python/NumPy rolling parity, existing Trend/Flow/Positioning/Structure
  fixtures, single-row/batch equivalence, future-append invariance, and explicit
  NaN/infinity behavior.
- The quantitative migration is not complete while any parity or safety gate
  fails, regardless of benchmark results.
- `btc_predictor.research.quant_benchmarks` provides seeded representative
  rolling, scoring, and portfolio timings. Timings are diagnostic only and have
  no fixed pass/fail threshold because correctness takes priority over speed.

## Determinism And Boundaries

- Simulation requires an explicit non-negative seed and uses NumPy `PCG64`.
- Resampling indices are drawn from the raw `PCG64` 64-bit words with modulo
  rejection (`PCG64_RAW_REJECTION_UNIFORM_INDEX_V1`) and permuted by
  Fisher-Yates over that same stream
  (`PCG64_RAW_FISHER_YATES_PERMUTATION_V1`), not through a `Generator`
  bounded-integer convenience method. The bit-generator stream is stable across
  NumPy versions; the algorithm layered on top of it is not guaranteed to be,
  and persisted seeded research evidence must replay on a later NumPy.
- Seeded simulations validate every generated sample. Accepted finite
  parameters either return finite `float64` samples or fail deterministically;
  they never return infinity or an unexpected NaN.
- Helpers do not access clocks, global random state, files, networks, databases,
  configuration, trading actions, or mutable application state.
- The package may depend on the Python standard library, NumPy, SciPy, and other
  modules within `btc_predictor.quant` only.
