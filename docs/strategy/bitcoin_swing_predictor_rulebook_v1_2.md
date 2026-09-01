# Bitcoin Swing Predictor — Rulebook & Scoring System v1.2

## 1. Strategy Objective

Build a **low-frequency Bitcoin swing trading system** designed to identify only high-conviction opportunities.

The system should prefer **NO TRADE** over mediocre setups.

### Target behavior

- Typical holding period: **1–6 weeks**
- Typical trade frequency: **1–4 entries per month**, potentially fewer
- Trade only when regime, setup, positioning, flows, price structure, and risk/reward align
- Enter small because initial structural stops may be wide
- Add only to profitable positions after market confirmation
- Never average down
- Use structural price levels for stops and trailing stops
- Let winners run while the environment remains supportive
- Reduce or exit when structure or conviction deteriorates

---

# 2. Core Trading Philosophy

The predictor should follow these principles:

1. **Default state = NO TRADE**
2. **Regime first, setup second, entry third**
3. **Structure determines stop location**
4. **Volatility determines the stop buffer**
5. **Risk budget determines position size**
6. **New confirmed structure determines trailing stops**
7. **Add only to winners**
8. **Notional exposure may increase while downside risk stays controlled**
9. **No fixed take-profit is required**
10. **Exit because the thesis weakens or structure fails, not merely because the trade is profitable**

---

# 3. System Architecture

The strategy definition is independent from the implementation language or numerical library.

```text
External Market / Reference Data
    │
    ▼
Point-in-Time Data Alignment
    │
    ▼
Quantitative Feature Layer
(NumPy / statistical transforms)
    │
    ├── Trend
    ├── Flow
    ├── Positioning
    ├── Volatility
    ├── Structure
    └── Regime
    │
    ▼
Setup Detector
    │
    ▼
Component Scores
    │
    ▼
Entry Conviction
    │
    ▼
Price-Level / Structure Engine
    │
    ▼
Risk / Reward Filter
    │
    ▼
Initial Position Sizing
    │
    ▼
Trade Lifecycle Engine
    │
    ├── Hold
    ├── Add
    ├── Trim
    └── Exit
```

The engine produces:

```text
REGIME
SETUP
DIRECTION

Trend Score
Regime Score
Flow Score
Positioning Score
Volatility Score
Structure Score

Entry Conviction
Hold Conviction
Add Conviction

Entry Zone
Invalidation Level
Initial Stop
Target Risk
Initial Position Size

ACTION:
NO TRADE / WATCH / ENTER / HOLD / ADD / TRIM / EXIT
```

The same mathematical definitions must be shared by:

```text
Advisory engine
Paper-trading engine
Historical backtester
Research evaluator
```

The backtester must not maintain separate formulas for scoring, position sizing,
risk-at-stop, R/R, or portfolio accounting.

---

# 3A. Canonical Data & Point-in-Time Policy

The system must explicitly distinguish three concepts:

```text
canonical_reference_price
market_data_sources
execution_venue
```

They are not assumed to be the same.

> [!IMPORTANT]
> **Current source-policy status**
>
> The following subsection records the provisional source policy that existed
> when Rulebook v1.2 was defined.
>
> It is not authoritative for the current empirical price-source decision.
>
> Current source-policy authority:
> [PRICE_SOURCE_POLICY_V1](../policies/price_source_policy_v1.md)
>
> Current production canonical reference: **UNRESOLVED**
>
> Bitstamp's sole-canonical candidate was empirically **REJECTED**.

## 3A.1 Provisional Phase 1 Price-Source Policy

Pending final validation, the preferred source hierarchy is:

| Role | Provisional Source | Instrument | Purpose |
|---|---|---|---|
| Canonical reference candidate + primary raw exchange OHLCV | Bitstamp | BTC/USD (`btcusd`) | Structural/reference candidate, 1h OHLCV, and volume |
| Required validation | Coinbase Exchange | BTC-USD | Independent cross-venue evidence |
| Required validation | Bitfinex | BTC/USD (`tBTCUSD`) | Independent cross-venue evidence |
| Optional institutional benchmark | Coin Metrics Community | BTC/USD pair candles (`btc-usd`) | Future V2 reference research |
| Research convenience only | yfinance | BTC-USD | Sanity checks / convenience research |
| Derivatives context | Binance and other derivatives venues | Venue-specific | Funding, OI, liquidations, perp activity |

The canonical reference price is used for:

```text
Trend
Structure
ATR / volatility
Breakouts / reclaims
Structural invalidation
Stops
Backtest structural reference
MFE / MAE
```

Raw exchange OHLCV is used for:

```text
Volume
Volume profile
Spot participation
Cross-exchange validation
Exchange-specific diagnostics
```

The eventual live execution venue is independent from the canonical reference
source.

## 3A.2 Point-in-Time Requirement

Every input used in a decision must satisfy:

[
available_at \le decision_time
]

This applies to:

- price observations
- ETF flows
- funding
- open interest
- futures basis
- liquidations
- macro data
- on-chain data
- confirmed swing levels
- AVWAP anchors
- volume-profile inputs
- all derived features

If a value was not available at the decision timestamp, it must not be used in
the historical or live decision.

## 3A.3 Source Provenance

Every price observation used by the strategy must preserve enough information
to reconstruct the source:

```text
provider
exchange
symbol
timeframe
observation_time
available_at / ingested_at
price_source_role
price_source_policy_version
fallback_used
```

Changing providers must not overwrite historical raw observations.

## 3A.4 Exchange-Specific Wick Policy

A single abnormal exchange wick should not automatically redefine canonical
market structure. Research must compare median cross-venue high, low, and close
and retain ATR-normalized high/low divergence distributions without relying on
a permanent hardcoded anomaly threshold.

The preferred principle is:

```text
Approved canonical reference series determines strategy structure.
Exchange-specific prices remain immutable and available for diagnostics and execution analysis.
```

Source validation must measure how provider choice changes:

```text
swing highs/lows
breakouts/reclaims
ATR
stop touches
MFE / MAE
trade outcomes
```

Before Phase 1 is considered fully validated, the provisional source policy must
be promoted to a versioned:

```text
PRICE_SOURCE_POLICY_V1
```

Promotion requires at least two years of synchronized Bitstamp, Coinbase, and
Bitfinex history, structured review of the top divergence events, and an
explicit persisted approval or rejection of the Bitstamp candidate. Coin
Metrics credentials or historical entitlement are optional and do not block
Phase 1.

`BTC_REFERENCE_COMPOSITE_V1` is reserved for a separate post-Phase-1 research
ticket. It is not part of the Phase 1 strategy or this policy implementation.

---

# 4. Primary Component Scores

Each major component is normalized to:

\[

0 \rightarrow 100

\]

The Phase 1 v1.2 Entry Conviction score uses only **direct, non-nested**
component scores:

\[

EntryConviction =

0.25Trend

+0.25Flow

+0.1875Positioning

+0.125Volatility

+0.1875Structure

\]

These weights are the exact re-normalization of the prior direct Entry Conviction
weights after removing Regime from the arithmetic.

Regime remains important, but it is treated as **market context / setup
eligibility**, not as a second copy of Trend, Flow, Positioning, and Volatility
inside Entry Conviction.

The weights remain **starting values for research**, not permanent constants.

## 4.1 Factor-Separation Principle

Phase 1 distinguishes:

```text
CONTEXT / GATES
Regime
Setup eligibility
Hard system flags
Structural-stop validity
R/R validity
Risk-at-stop

DIRECT QUALITY SCORES
Trend
Flow
Positioning
Volatility
Structure
Entry Conviction
Hold Score
Add Score
```

A composite score should not mechanically contain another composite score that
already contains overlapping underlying factors unless that overlap is:

```text
explicitly intentional
quantified
versioned
and validated by ablation / sensitivity research
```

Therefore v1.2 applies these rules:

1. `RegimeScore` is not an arithmetic input to `EntryConviction`.
2. `RegimeScore` is not an arithmetic input to `HoldScore`.
3. `HoldScore` is not an arithmetic input to `AddScore`.
4. `RRQuality` is not an arithmetic input to `StructureScore`.
5. Outer `StructureScore` does not score `Confluence` again because confluence is
   already represented inside `LevelStrength`.
6. R/R remains an independent hard asymmetry filter.
7. Empirical correlation between distinct factors is allowed and must be measured;
   v1.2 removes **mechanical nesting**, not natural market correlation.

This keeps the deterministic model interpretable while allowing later research
to determine whether Trend, Flow, Positioning, Volatility, and Structure provide
independent predictive information.

## 4.2 Numerical Implementation Principle

The mathematical definitions in this rulebook are the strategy.

Vectorization, NumPy/SciPy migration, database optimization, caching, or other
engineering changes must not alter strategy behavior unless a new strategy or
configuration version is explicitly created.

The preferred implementation boundary is:

```text
PostgreSQL        → durable source of truth
pandas / Polars  → point-in-time alignment
NumPy            → numerical computation
SciPy            → statistical primitives
Python domain    → strategy decisions and hard rules
PostgreSQL        → persisted outputs and lifecycle state
```

Missing numerical inputs must not be silently converted to zero.

Internal numerical calculations should use a consistent high-precision floating
point convention, with deterministic tolerance rules for parity testing.


---

# 5. Trend Score

The Trend Score should be dominated by weekly and multi-week price behavior.

## 5.1 Inputs

### 4-week momentum

\[

M_4=\frac{P_t}{P_{t-28}}-1

\]

Normalize using trailing historical data:

\[

Z_{M4}=

\frac{M_4-\mu}{\sigma}

\]

### 12-week momentum

\[

M_{12}=

\frac{P_t}{P_{t-84}}-1

\]

\[

Z_{M12}=zscore(M_{12})

\]

### Distance from 20-week moving average

\[

D_{20W}=

\frac{P_t-MA_{20W}}{MA_{20W}}

\]

### Weekly market structure

Suggested mapping:

| Weekly Structure | Raw Score |
|---|---:|
| Higher high + higher low | +1.0 |
| Higher low only | +0.5 |
| Mixed | 0.0 |
| Lower high only | -0.5 |
| Lower high + lower low | -1.0 |

### Distance from 52-week high

\[

D_{52H}=

\frac{P_t-H_{52W}}{H_{52W}}

\]

---

## 5.2 Trend Composite

Initial formulation:

\[

TrendRaw =

0.30Z_{M4}

+0.30Z_{M12}

+0.20Z_{20W}

+0.15S_{structure}

+0.05Z_{52H}

\]

Convert to 0–100:

\[

TrendScore=100\times\Phi(TrendRaw)

\]

where \(\Phi\) is the standard normal CDF.

### Interpretation

| Trend Score | Meaning |
|---:|---|
| 80–100 | Strong bullish trend |
| 65–80 | Bullish |
| 45–65 | Mixed |
| 25–45 | Bearish |
| 0–25 | Strong bearish |

### Initial rules

Normal long:

\[

TrendScore \ge 65

\]

Trend continuation:

\[

TrendScore \ge 70

\]

Bullish reset may allow:

\[

TrendScore \ge 55

\]

---

# 6. Flow Score

The Flow Score answers:

> Is real capital entering or leaving Bitcoin?

## 6.1 Inputs

### 5-day ETF flow

\[

ETF_5=\sum_{i=0}^{4}NetFlow_{t-i}

\]

Normalize:

\[

ETFNorm_5=

\frac{ETF_5}{TotalETFAssets}

\]

### 20-day ETF flow

\[

ETFNorm_{20}=

\frac{\sum_{i=0}^{19}NetFlow_{t-i}}

{TotalETFAssets}

\]

### Flow acceleration

\[

FlowAccel=

ETFNorm_5-\frac{ETFNorm_{20}}{4}

\]

### Spot-vs-derivatives participation

\[

SpotDominance=

z(SpotVolumeGrowth)-z(PerpVolumeGrowth)

\]

### Spot-vs-perp CVD

\[

CVDSpread=

z(SpotCVD)-z(PerpCVD)

\]

---

## 6.2 Flow Composite

\[

FlowRaw =

0.30z(ETFNorm_5)

+0.25z(ETFNorm_{20})

+0.20z(FlowAccel)

+0.15z(CVDSpread)

+0.10z(SpotDominance)

\]

Map the result to 0–100.

### Phase 1 fallback

If spot/perp participation or CVD data is unavailable in Phase 1, compute a

core ETF-only flow score using re-normalized weights:

\[

FlowRaw_{core} =

0.40z(ETFNorm_5)

+0.35z(ETFNorm_{20})

+0.25z(FlowAccel)

\]

The output must record which flow model was used:

```text

FLOW_MODEL = ETF_CORE

FLOW_MODEL = ETF_SPOT_PERP_FULL

```

Do not silently substitute zeroes for missing flow inputs.

### Interpretation

| Flow Score | Meaning |
|---:|---|
| 75–100 | Strong accumulation |
| 60–75 | Supportive |
| 45–60 | Neutral |
| 30–45 | Deteriorating |
| 0–30 | Strong outflow / distribution |

### Initial long rule

\[

FlowScore \ge 55

\]

For capitulation/reversal setups, absolute flow may still be weak, but **flow acceleration should be improving**.

---

# 7. Positioning Score

The Positioning Score measures whether leverage and derivatives positioning are **healthy for the trade**, not merely bullish or bearish.

A high score means supportive positioning without excessive crowding.

---

## 7.1 Funding Health

Use a 7-day average funding rate:

\[

FZ=zscore(Funding_{7dAvg},180d)

\]

For bullish setups, the preferred region may be around neutral to moderately positive.

Example health function:

\[

FundingHealth=

100e^{-0.5((FZ-0.25)/1.25)^2}

\]

The parameters are research variables.

---

## 7.2 Open Interest Growth

\[

OI_7=

\frac{OI_t}{OI_{t-7}}-1

\]

Conceptual interpretation:

| OI Behavior | Interpretation |
|---|---|
| Mild contraction | Neutral / reset |
| Modest expansion | Healthy confirmation |
| Strong expansion | Caution |
| Extreme expansion | Crowded / liquidation risk |

Use rolling normalization rather than permanent fixed percentage thresholds.

---

## 7.3 OI Intensity

\[

OIIntensity=

\frac{AggregateOI}{BTCMarketCap}

\]

Convert to a rolling historical percentile.

Very high OI intensity means unusually high embedded leverage.

---

## 7.4 Futures Basis

Annualized basis:

\[

Basis=

\left(\frac{Futures}{Spot}-1\right)

\frac{365}{DaysToExpiry}

\]

Moderate positive basis can be healthy.

Extreme positive basis indicates leverage/carry excess.

Negative basis may indicate stress.

---

## 7.5 Positioning Composite

\[

PositioningScore=

0.35FundingHealth

+0.30OIHealth

+0.20BasisHealth

+0.15LeverageHealth

\]

### Initial rules

New long:

\[

PositioningScore \ge 60

\]

Add to long:

\[

PositioningScore \ge 70

\]

If:

\[

PositioningScore < 40

\]

then:

```text

NO ADDING

```

regardless of price strength.

---

# 8. Volatility Score

Volatility should answer:

1. Is the market orderly enough to trade?
2. Is volatility compressed, normal, or stressed?

## 8.1 Inputs

\[

RV_7,\ RV_{20},\ RV_{60}

\]

Compression ratio:

\[

CompressionRatio=

\frac{RV_7}{RV_{60}}

\]

Volatility percentile:

\[

VolPercentile=

Percentile(RV_{20},2yr)

\]

---

## 8.2 Standard Trend Environment

Preferred characteristics:

```text

RV7 / RV60 < 1

RV20 near historical median

No extreme downside shock

No liquidation cascade

```

Potential composite:

\[

VolatilityScore=

0.5CompressionScore+

0.5OrderlinessScore

\]

For capitulation setups, extreme volatility can be part of the opportunity, so the interpretation is setup-specific.

---

# 9. Structure / Price-Level Score

The Structure Score is central to the strategy.

The engine should identify major price levels, group nearby levels into zones, and evaluate the quality of those zones.

## 9.1 Candidate Levels

Prioritize:

- Monthly swing highs/lows
- Weekly swing highs/lows
- Major breakout/reclaim levels
- Previous monthly high/low
- Volume-profile High Volume Nodes
- Value Area High / Low
- Point of Control
- Anchored VWAPs from important market events
- Major consolidation boundaries
- Daily structure only for entry refinement

Avoid relying on obvious round numbers or moving averages alone.

---

## 9.2 Level Strength

For each candidate level \(L\):

\[

LevelStrength =

w_1Timeframe+

w_2Touches+

w_3ReactionMagnitude+

w_4Volume+

w_5Confluence

\]

Initial Phase 1 weights:

\[

LevelStrength =

0.30Timeframe+

0.25Touches+

0.25ReactionMagnitude+

0.20Confluence

\]

Volume-profile and AVWAP confluence are optional Phase 1 enhancements. If they

are not implemented, do not score them as zero; omit them and use the core

weights above.

### Timeframe Score

| Timeframe | Score |
|---|---:|
| Monthly | 100 |
| Weekly | 80 |
| Daily | 50 |
| Intraday | 20 |

### Touch Score

Example initial mapping:

| Clean Reactions | Score |
|---:|---:|
| 1 | 50 |
| 2 | 75 |
| 3 | 90 |
| 4+ | 75 |

Too many tests can weaken a level.

### Reaction Magnitude

Measure historical reaction from the level relative to ATR:

\[

ReactionScore=

f\left(\frac{ReactionMagnitude}{ATR}\right)

\]

### Confluence

Increase strength when multiple concepts overlap:

```text

Weekly low

+ prior breakout
+ AVWAP
+ High Volume Node

```

Treat nearby levels as one **support/resistance cluster**, not as independent lines.

For v1.1 research, prefer volatility-normalized level distance:

[
Distance_{ij}=
\frac{|L_i-L_j|}{ATR}
]

This allows the same structural logic to adapt across low- and high-volatility
BTC regimes.

The existing fixed/fractional distance method may remain as a compatibility and
benchmark method until historical comparison is complete.


---

## 9.3 Entry Location

For longs:

\[

DistanceToSupport=

\frac{Entry-Support}{ATR}

\]

Entries closer to high-quality support clusters receive better scores, provided the trade is not already structurally invalid.

---

## 9.4 Structure Composite

v1.2 removes mechanical double-counting between structure and risk/reward.

`RRQuality` is no longer part of `StructureScore`, because R/R is evaluated
independently as a hard asymmetry filter.

`Confluence` remains inside `LevelStrength` and is not scored a second time at
the outer Structure layer.

The prior unique outer weights were `0.45 LevelStrength + 0.25 EntryLocation`.
Re-normalizing those weights to 1.0 gives:

\[

StructureScore=

0.642857LevelStrength

+0.357143EntryLocation

\]

Phase 1 should compute `LevelStrength` and `EntryLocation` from confirmed
weekly/monthly levels, breakout/reclaim levels, and level clusters.

R/R, structural target selection, and confluence should still be calculated and
persisted where useful for diagnostics and downstream filters, but they do not
receive a second outer `StructureScore` contribution.

Volume-profile and AVWAP evidence may improve `LevelStrength` later but must not
be required for the first deterministic implementation.

### Initial rules

New long:

\[

StructureScore \ge 70

\]

Hard reject:

\[

StructureScore < 60

\]

---

# 10. Regime Score

Regime is slower-moving than the setup.

Initial formulation:

\[

RegimeScore =

0.35Trend

+0.20Flow

+0.15Macro

+0.10OnChain

+0.10Volatility

+0.10Liquidity

\]

### Phase 1 fallback

If macro, on-chain, or liquidity inputs are unavailable in Phase 1, use a

reweighted core regime score:

\[

RegimeScore_{core} =

0.45Trend

+0.25Flow

+0.15Volatility

+0.15Positioning

\]

The recommendation output must identify the regime model used:

```text

REGIME_MODEL = CORE_MARKET_ONLY

REGIME_MODEL = FULL_MACRO_ONCHAIN_LIQUIDITY

```

Smooth the score:

\[

R_t=

0.7R_{t-1}

+

0.3R_{new}

\]

This prevents regime classification from flipping too frequently.

## Regime Classification

| Score | Regime |
|---:|---|
| 80–100 | Strong Bull |
| 65–80 | Bull |
| 55–65 | Mild Bull |
| 45–55 | Neutral |
| 35–45 | Mild Bear |
| 20–35 | Bear |
| 0–20 | Strong Bear |

---

# 11. Setup Archetypes

Phase 1 should recognize only a small number of interpretable setups.

---

## Setup A — Bull Trend Continuation

### Hard requirements

\[

Regime \ge 65

\]

\[

Trend \ge 70

\]

\[

Flow \ge 55

\]

\[

Positioning \ge 60

\]

\[

Structure \ge 70

\]

Also require:

- No stress flag
- No severe crowding
- Initial R/R ≥ 2
- Entry Conviction ≥ 80

Typical context:

```text

Bullish weekly regime

Controlled consolidation / pullback

Healthy ETF or spot demand

Funding moderate

OI not excessive

Volatility normal or compressed

Support cluster nearby

```

---

## Setup B — Bullish Reset

Potentially one of the highest-priority setups.

### Requirements

- Broader bull regime intact
- Medium-term trend still positive
- Meaningful correction from local high
- Funding materially reset
- OI deleveraged or stabilized
- Strong support/reclaim zone nearby
- Flow deterioration slowing or reversing
- Price structure beginning to recover

Useful v1 correction range:

\[

8\\%-25\\%

\]

from local high, but this should later be volatility-normalized.

Initial deterministic thresholds:

```text

RegimeScore >= 55

TrendScore >= 55

CorrectionFromLocalHigh between 8% and 25%

FundingHealth improving over 7 trading days

OIHealth improving or stable over 7 trading days

FlowAccel improving over 5 trading days

StructureScore >= 70

Entry trigger confirmed

Entry Conviction >= 80

Initial R/R >= 2

```

Key signal is **improvement**:

\[

\Delta Positioning > 0

\]

\[

\Delta Flow > 0

\]

\[

\Delta Structure > 0

\]

---

## Setup C — Capitulation Reversal

Rare and strict.

Potential evidence:

- RV above 90th–95th percentile
- Large liquidation event
- OI collapse
- Deeply negative funding
- Large realized losses
- Major long-term support
- Price reclaim
- Positive flow reversal

Require a **reclaim or higher-low confirmation**.

Do not buy solely because the market looks oversold.

---

## Setup D — Bearish Distribution

Short setups should require stronger evidence than longs.

Potential requirements:

- Trend weakening or structurally bearish
- Flow deteriorating
- Positioning excessively crowded
- Failed breakout / lower high
- Support breakdown
- Macro or liquidity regime deteriorating

Suggested initial short threshold:

\[

EntryConviction_{short} \ge 85

\]

---

# 12. Entry Triggers

Phase 1 should support only three entry trigger types.

## 12.1 Reclaim

For a long:

```text

Price trades below / around major level

→ closes back above level

→ holds or confirms

```

## 12.2 Breakout + Retest

```text

Breakout

→ pullback

→ former resistance holds as support

→ continuation confirmation

```

Do not chase the first large breakout candle.

## 12.3 Higher-Low Confirmation

```text

Selloff

→ bounce

→ pullback

→ higher low

→ break above local pivot

```

This is especially useful for bullish-reset and capitulation-reversal setups.

---

# 13. Entry Conviction

v1.2 uses a de-nested direct-component formula:

\[

C_{entry} =

0.25Trend

+0.25Flow

+0.1875Positioning

+0.125Volatility

+0.1875Structure

\]

Regime is evaluated separately by the setup/context layer and is not included
again inside Entry Conviction.

This means a weak or invalid regime can still block a trade even when direct
entry quality is high, but Regime does not mechanically re-inject Trend, Flow,
Positioning, or Volatility into the score.

## Interpretation

| Entry Conviction | Action |
|---:|---|
| <70 | Ignore |
| 70–79 | Watchlist |
| 80–84 | Valid trade |
| 85–89 | Strong setup |
| 90+ | Exceptional |

Actual trade requires:

\[

C_{entry} \ge 80

\]

and all hard filters must pass.

---

# 14. Hard Vetoes

A high score cannot override a failed hard rule.

Examples:

- No valid structural stop
- Structural stop too far to size sensibly
- Initial R/R below threshold
- Extreme abnormal volatility
- Missing or unreliable data
- Price has already moved too far beyond the intended entry zone
- Severe positioning crowding
- Liquidity conditions materially impaired
- Setup no longer matches its archetype

Formal logic:

\[

Trade=

HighConviction

\land

AllHardFiltersPassed

\]

---

# 15. Initial Risk / Reward

Before entry:

\[

RR=

\frac{PotentialReward}{RiskToInvalidation}

\]

For Phase 1, `PotentialReward` should be measured to the nearest credible

upside structural reference, selected in this order:

1. Nearest major weekly/monthly resistance cluster
2. Prior local swing high
3. Prior range high
4. Conservative measured move from the active setup

If no credible upside reference exists, the R/R filter fails.

Initial minimum:

\[

RR \ge 2

\]

Preferred:

\[

RR \ge 2.5-3

\]

This is used to judge asymmetry at entry.

It does **not** create a fixed take-profit.

---

# 16. Stop-Loss Rules

## 16.1 Structural Stop

For a long:

\[

Stop=

StructuralInvalidation-

VolatilityBuffer

\]

For a short:

\[

Stop=

StructuralInvalidation+

VolatilityBuffer

\]

Recommended initial research formula:

\[

Buffer=

\max(0.3ATR_{20},LevelNoiseEstimate)

\]

Test:

\[

0.25ATR,\ 0.50ATR,\ 0.75ATR

\]

The exact value must be backtested.

---

## 16.2 Stop Principles

- Stops should be based on **zones**, not exact lines
- Avoid placing stops immediately beyond obvious public levels
- Stop should represent thesis invalidation
- Stop should never be widened after entry
- The structural timeframe should match the trade timeframe

---

# 17. Initial Position Sizing

Initial risk should be conservative.

Suggested starting schedule:

| Entry Conviction | Risk at Initial Stop |
|---:|---:|
| 80–84 | 0.35% NAV |
| 85–89 | 0.50% NAV |
| 90+ | 0.60% NAV |

Position size:

\[

PositionNotional=

\frac{NAV\times RiskBudget}{StopDistance\\%}

\]

Example:

```text

NAV            $100,000

Risk budget    0.50% = $500

Entry          $100,000 BTC

Stop           $90,000 BTC

Stop distance  10%

Position notional = $5,000

```

The wide stop automatically forces a small initial position.

---

# 18. Pyramiding / Add-to-Winner Rules

The system follows an **anti-martingale** principle:

> Add to winners, never to losers.

Suggested tranche framework:

| Stage | Relative Final Position |
|---|---:|
| Initial | 40% |
| Add #1 | +35% |
| Add #2 | +25% |

These percentages are research parameters.

---

## 18.1 Add Requirements

An add requires **all** of the following:

1. Existing position is profitable
2. New bullish structure has formed
3. Stop can be raised
4. Regime remains supportive
5. Flow remains supportive
6. Positioning is not crowded
7. Add Conviction ≥ 85
8. Total risk at the revised stop remains within portfolio limit

Absolute rule:

```text

NO AVERAGING DOWN

```

---

# 19. Risk-at-Stop Constraint

For multiple tranches, use an unambiguous quantity-based definition.

If (Q_i) is BTC quantity:

[
RiskAtStop=
\sum_i
Q_i\times|Entry_i-Stop|
]

If position size is represented as notional value (N_i):

[
RiskAtStop=
\sum_i
N_i
\times
\left|
\frac{Entry_i-Stop}{Entry_i}
\right|
]

For a long position, implementations may equivalently floor already-profitable
tranches at zero downside contribution when measuring loss from the current
portfolio state:

[
RiskAtStop_{long}=
\sum_i
N_i
\max
\left(
\frac{Entry_i-Stop}{Entry_i},
0
\right)
]

The exact convention used for pre-entry risk, current portfolio risk, and
realized locked-in profit must be explicit and consistent across advisory,
paper trading, and backtesting.

Suggested Phase 1 maximum:

[
RiskAtStop \le 0.75\%-1.00\% NAV
]

The key objective is:

> Notional exposure can increase while total downside risk stays bounded.

---

# 20. Hold Score

Once a trade is open, use a separate **de-nested** score.

Regime remains a separately persisted lifecycle context / invalidation input and
is not included again inside Hold Score.

The prior direct Hold components summed to 0.75 after Regime was removed.
Re-normalizing them gives:

\[

HoldScore =

0.2666667Trend+

0.2666667Flow+

0.20Positioning+

0.1333333Structure+

0.1333333MomentumPersistence

\]

Regime deterioration can still trigger defensive management or
`REGIME_INVALIDATION` independently of Hold Score.

## Interpretation

| Hold Score | Action |
|---:|---|
| ≥85 | Hold / possible add |
| 70–85 | Hold |
| 60–70 | Hold, no add |
| 50–60 | Defensive; tighten / consider trim |
| 40–50 | Trim |
| <40 | Exit |

The structural stop always remains an independent override.

---

# 21. Add Score

Adding should be harder than holding.

v1.2 removes `HoldScore` from the Add Score arithmetic because Hold already
contains Flow, Positioning, Structure, and momentum-related information.

The remaining direct Add components previously summed to 0.80. Re-normalizing
them gives:

\[

AddScore =

0.3125NewStructure

+0.25Flow

+0.1875Positioning

+0.125Momentum

+0.125RiskImprovement

\]

Hold quality and supportive Regime remain separate add requirements / lifecycle
context rather than nested score inputs.

Add threshold:

\[

AddScore \ge 85

\]

The existing Entry / Hold / Add score bands are retained as **provisional
compatibility thresholds** in v1.2. Because score distributions change after
de-nesting, BTC-185 must revalidate the thresholds before final Phase 1
promotion. Thresholds may not be silently changed without a versioned parameter
set.

A key input is:

\[

RiskImprovement

\]

If the existing stop has not improved materially, adding should be difficult.

---

# 22. Trailing Stop Engine

Trailing stops should advance only when new confirmed structure forms.

For a long:

\[

CandidateStop_t=

NewHigherLow-

VolatilityBuffer

\]

Then:

\[

Stop_t=

\max(Stop_{t-1},CandidateStop_t)

\]

For shorts, use the mirrored logic.

## Three Stages

### Stage 1 — Thesis Stop

Wide structural invalidation stop.

### Stage 2 — Confirmation Stop

After market confirmation and a new higher low, raise the stop under the new structure.

### Stage 3 — Profit-Protection Trail

As the trend matures, continue advancing the stop under meaningful higher lows.

No daily mechanical trailing is required.

---

# 23. Profit Management

No fixed take-profit is required.

Exit or reduce because the expected value deteriorates.

Primary reasons:

- Structural invalidation
- Regime deterioration
- Flow reversal
- Positioning excess
- Momentum deterioration
- Euphoria / distribution
- Stress event

## Conviction-Based Management

| Hold Conviction | Action |
|---:|---|
| ≥85 | Hold / potential add |
| 70–85 | Hold |
| 55–65 | Stop adding; tighten risk |
| 45–55 | Trim |
| <45 | Exit |

This can be tuned during research.

---

# 24. Hard System Flags

Create binary flags that can override ordinary scoring.

## STRESS

Possible triggers:

- Extreme realized volatility percentile
- Liquidation cascade
- Disorderly downside move
- Abnormal basis/funding
- Systemic market shock

Effects:

```text

NO ADDING

REDUCE MAX EXPOSURE

POTENTIALLY BLOCK NEW TRADES

```

---

## CROWDING

Triggered by excessive leverage / funding / basis.

Effects:

```text

NO ADDING

REDUCE ENTRY QUALITY

POTENTIALLY TIGHTEN PROFIT PROTECTION

```

---

## EUPHORIA

Potential combination:

```text

Strong price extension

+ extreme funding
+ rapidly rising OI
+ weakening spot/ETF flow

```

Effects:

```text

NO ADDING

POTENTIAL TRIM

TIGHTEN TRAILING LOGIC

```

---

## CAPITULATION

Potential combination:

```text

Extreme downside volatility

+ OI collapse
+ negative funding
+ liquidation spike
+ realized losses

```

This does not automatically mean BUY.

It enables the **Capitulation Reversal** setup only after confirmation.

---

## DATA_QUALITY_FAIL

If critical data is missing, stale, inconsistent, or suspicious:

```text

NO NEW TRADES

NO NEW ADDS

```

---

# 25. No-Chase Rule

If price moves materially beyond the intended entry zone before execution:

```text

NO TRADE

```

Do not lower standards because the market is moving.

The system is allowed to miss trades.

---

# 26. Trade Lifecycle

```text

START

  │

  ▼

Determine Regime

  │

  ├── Untradable / Stress?

  │        └── NO TRADE

  │

  ▼

Detect Setup

  │

  ├── No recognized setup

  │        └── NO TRADE

  │

  ▼

Setup Quality passes?

  │

  ├── No ──→ NO TRADE

  │

  ▼

Valid Price Structure?

  │

  ├── No ──→ NO TRADE

  │

  ▼

Valid Structural Stop?

  │

  ├── No ──→ NO TRADE

  │

  ▼

Initial R/R >= 2?

  │

  ├── No ──→ NO TRADE

  │

  ▼

Entry Conviction >= 80?

  │

  ├── No ──→ WATCH

  │

  ▼

ENTER SMALL

  │

  ▼

Market Confirms?

  │

  ├── No → Hold Small / Stop Out

  │

  ▼

Structure Improves + Add Score >= 85?

  │

  ├── Yes → Raise Stop → ADD

  │

  ▼

Further Confirmation?

  │

  ├── Yes → Raise Stop → ADD

  │

  ▼

Manage Winner

  │

  ├── Structure Healthy → HOLD

  │

  ├── Conviction Weakens → TRIM

  │

  └── Structure Invalidated → EXIT

```

---

# 27. Predictor Explanation Output

Every signal should explain why it exists.

Example:

```text

BTC SWING ENGINE

Regime:

BULL — 74

Setup:

BULLISH RESET

Entry Conviction:

87 / 100

Trend:

76

✓ 12-week trend positive

✓ above 20W MA

✓ weekly structure intact

Flow:

84

✓ 5d ETF flows positive

✓ flow acceleration positive

✓ spot buying stronger than perp buying

Positioning:

81

✓ funding reset

✓ OI reduced

✓ basis normal

✓ leverage below extreme percentile

Volatility:

68

✓ selloff volatility declining

! still above median

Structure:

92

✓ weekly support cluster

✓ prior breakout level

✓ anchored VWAP confluence

✓ favorable invalidation

Entry:

99,000–101,000

Invalidation:

91,500

Stop:

89,800

Initial R/R:

3.1

Risk:

0.50% NAV

Position:

6.0% NAV

ACTION:

ENTER INITIAL TRANCHE

```

---

# 28. Backtest and Research Rules

The system should be judged by **selective trading quality**, not raw prediction accuracy.

Primary metrics:

- Expectancy
- Average R per trade
- Sharpe
- Sortino
- Calmar
- Max drawdown
- Return per trade
- Win rate
- Profit factor
- Average winner
- Average loser
- Time in market
- Turnover
- Number of trades
- Longest drawdown
- Longest losing streak

Additional data-source robustness metrics:

- Canonical-price source sensitivity
- Missing-bar sensitivity
- Cross-provider close divergence
- Cross-provider high/low divergence
- Structural-level divergence
- Stop-touch divergence
- Isolated-wick sensitivity
- MFE / MAE source sensitivity

Phase 1 validation should verify that results are not materially dependent on a
single provider anomaly or a small number of exchange-specific wicks.

Additional score-architecture diagnostics:

```text
direct component correlation matrix
rank-correlation matrix
analytical effective-weight decomposition
factor / component ablation
trade-decision overlap after ablation
conviction monotonicity
regime-conditioned factor stability
setup-conditioned factor stability
factor concentration / effective-rank diagnostic
```

Phase 1 should explicitly compare the retired nested v1.1 scoring architecture
with the de-nested v1.2 architecture as a **research benchmark only**. v1.1 must
not silently remain the production scoring definition after v1.2 is promoted.


---

# 29. Research Objective

The objective should reward strong returns per trade and penalize overtrading and drawdown.

Conceptual objective:

\[

Objective=

Sharpe

+0.5Calmar

+0.25AvgRPerTrade

-0.25TurnoverPenalty

-0.25DrawdownPenalty

\]

Possible trade-frequency constraints:

\[

TradesPerYear \le 36

\]

or more conservatively:

\[

TradesPerYear \le 24

\]

The strategy should not be forced to meet a minimum number of trades.

---

# 30. Threshold Robustness

Do not accept brittle parameters.

Example:

Test:

\[

EntryThreshold=

75,\ 77.5,\ 80,\ 82.5,\ 85

\]

Likewise sweep:

- Trend minimum
- Flow minimum
- Positioning minimum
- Structure minimum
- R/R minimum
- Stop buffer
- Hold threshold
- Add threshold
- Risk-per-trade schedule

Prefer broad parameter regions with stable performance over a single optimized point.

Because v1.2 changes the score architecture, threshold robustness must include
revalidation of:

```text
Entry Conviction bands
Structure minimum / hard-reject bands
Hold Score bands
Add Score threshold
```

Do not assume the v1.1 numerical thresholds preserve the same percentile meaning
under the v1.2 score distributions.

---

# 31. Phase 1 Rules Summary

## New Trade

A new trade should generally require:

```text

Recognized setup

+ supportive regime
+ sufficient trend
+ acceptable flow
+ healthy positioning
+ valid volatility environment
+ strong price structure
+ valid structural stop
+ initial R/R >= 2
+ Entry Conviction >= 80
+ no hard veto

```

## Add

```text

Existing trade profitable

+ new structural confirmation
+ stop can improve
+ regime supportive
+ flow supportive
+ positioning healthy
+ Add Score >= 85
+ total risk at stop remains bounded

```

## Hold

```text

Structure intact

+ Hold Score remains acceptable

```

## Trim

```text

Conviction deteriorates

and/or

EUPHORIA / CROWDING emerges

```

## Exit

```text

Structural invalidation

or

Hold Score collapses

or

environment changes enough to invalidate expected value

```

---

# 32. Core Rules to Never Violate

1. **Default = NO TRADE**
2. **Never average down**
3. **Never widen a stop after entry**
4. **Never size the stop around the desired position**
5. **Structure determines the stop**
6. **Risk determines the position size**
7. **Adding requires improved structure and bounded risk**
8. **Do not chase missed entries**
9. **Do not force trade frequency**
10. **Do not optimize for accuracy at the expense of expectancy**
11. **Do not allow a high score to override a hard veto**
12. **Do not use future information in scoring or normalization**
13. **Do not silently change the canonical price source inside a historical series**
14. **Do not let one exchange-specific anomaly redefine canonical structure without validation**
15. **Advisory, paper-trading, and backtest paths must use the same shared quantitative formulas**
16. **Numerical refactors must pass parity tests before they replace validated implementations**
17. **Do not mechanically double-count a factor through nested composite scores unless the overlap is explicit, quantified, versioned, and validated**
18. **Keep R/R as an independent asymmetry filter rather than rewarding it twice inside Structure and again as a hard veto**


---

# 33. Version Status

**Version:** 1.2

**Purpose:** Phase 1 deterministic BTC swing predictor specification with
explicit canonical data policy, point-in-time rules, de-nested scoring contracts,
shared quantitative definitions, structural-risk rules, and controlled
implementation migration.

**Current architecture status:**

```text
PostgreSQL data foundation          established
Point-in-time ingestion             established
Trend engine                        established
Flow engine                         established
Positioning engine                  established
Structure engine                    established; v1.2 de-nesting migration required
Score factor-separation contract     specified in v1.2; implementation pending
Volatility primitives               substantially established

Quantitative NumPy/SciPy core       next migration stage
Entry Conviction                    remaining Phase 1 work
Risk engine                         remaining Phase 1 work
Lifecycle / pyramiding              remaining Phase 1 work
Paper trader                        remaining Phase 1 work
Event-driven backtester             remaining Phase 1 work
```

**Provisional canonical BTC price policy:**

```text
Reference candidate + raw OHLCV:
Bitstamp BTC/USD

Required validation:
Coinbase BTC-USD
Bitfinex BTC/USD

Optional institutional benchmark:
Coin Metrics Community BTC/USD pair candles

yfinance:
research convenience only
```

This source policy remains provisional until cross-provider historical
validation across the three required exchange providers is complete and
`PRICE_SOURCE_POLICY_V1` is explicitly promoted. Coin Metrics access is not a
Phase 1 completion dependency.

**Next step:**

```text
Validate canonical price-source policy
        ↓
Complete NumPy/SciPy quant-core migration with parity tests
        ↓
Migrate Structure Score to v1.2 de-nested definition
        ↓
Complete Volatility Score
        ↓
Validate factor-overlap / de-nested scoring contract
        ↓
Complete Entry Conviction / vetoes
        ↓
Complete risk and position lifecycle
        ↓
Run autonomous paper portfolio
        ↓
Build event-driven backtester
        ↓
Walk-forward and source-sensitivity validation
```
