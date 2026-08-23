# Bitcoin Swing Predictor — Rulebook & Scoring System v1

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

```text
Market Data
    │
    ▼
Regime Model
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

---

# 4. Primary Component Scores

Each major component is normalized to:

\[
0 \rightarrow 100
\]

The initial Entry Conviction score is:

\[
EntryConviction =
0.20Trend
+0.20Regime
+0.20Flow
+0.15Positioning
+0.10Volatility
+0.15Structure
\]

These weights are **starting values for research**, not permanent constants.

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

\[
StructureScore=
0.45LevelStrength
+0.25EntryLocation
+0.20RRQuality
+0.10Confluence
\]

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
8\%-25\%
\]

from local high, but this should later be volatility-normalized.

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

Initial formula:

\[
C_{entry} =
0.20Trend
+0.20Regime
+0.20Flow
+0.15Positioning
+0.10Volatility
+0.15Structure
\]

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
\frac{NAV\times RiskBudget}{StopDistance\%}
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

For multiple tranches:

\[
RiskAtStop=
\sum_i
Position_i\times|Entry_i-Stop|
\]

Suggested Phase 1 maximum:

\[
RiskAtStop \le 0.75\%-1.00\% NAV
\]

The key objective is:

> Notional exposure can increase while total downside risk stays bounded.

---

# 20. Hold Score

Once a trade is open, use a separate score:

\[
HoldScore =
0.25Regime+
0.20Trend+
0.20Flow+
0.15Positioning+
0.10Structure+
0.10MomentumPersistence
\]

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

Suggested formula:

\[
AddScore =
0.20HoldScore
+0.25NewStructure
+0.20Flow
+0.15Positioning
+0.10Momentum
+0.10RiskImprovement
\]

Add threshold:

\[
AddScore \ge 85
\]

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
| 80+ | Hold / potential add |
| 65–80 | Hold |
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

---

# 33. Version Status

**Version:** 1.0  
**Purpose:** Phase 1 deterministic BTC swing predictor specification  
**Next step:** convert the rules into implementation tickets, data contracts, exact feature definitions, and walk-forward backtest tests.
