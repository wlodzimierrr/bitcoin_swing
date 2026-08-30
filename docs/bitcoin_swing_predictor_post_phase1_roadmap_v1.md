# Bitcoin Swing Predictor — Post-Phase-1 Research & Development Roadmap v1.0

## 1. Purpose

This document defines the recommended roadmap **after Phase 1 is complete**.

The objective is not to make the system more complicated for its own sake.

The objective is to move from:

```text
hand-designed deterministic trading logic
```

to:

```text
empirically understood
point-in-time validated
out-of-sample tested
champion/challenger
institutional-quality research process
```

The core research question changes from:

> What indicator should we add?

to:

> What conditional relationship persists out of sample, adds independent information, and improves the distribution of trading outcomes?

Phase 1 builds a trading theory.

Phase 2 and beyond should try as hard as possible to **disprove, simplify, and improve it**.

---

# 2. Guiding Principles

The post-Phase-1 process should follow these rules:

1. **Freeze a deterministic benchmark before changing it.**
2. **Start live shadow trading as soon as the Phase-1 engine is trustworthy.**
3. **Do not wait for ML before collecting live out-of-sample evidence.**
4. **Build an alpha-research dataset, not merely a price database.**
5. **Measure information content before optimizing weights.**
6. **Run aggressive ablation tests.**
7. **Separate mechanical score overlap from natural market correlation.**
8. **Study factors conditionally by regime and setup.**
9. **Separate directional alpha from trade-expression quality.**
10. **Require every new dataset to prove incremental out-of-sample value.**
11. **Use simple challenger models before complex ML.**
12. **Track stability through time, not just full-sample averages.**
13. **Control for multiple-hypothesis / data-mining risk.**
14. **No challenger model may modify production automatically.**
15. **Promotion must be manual, versioned, and walk-forward validated.**
16. **Do not optimize for win rate at the expense of expectancy.**
17. **Do not weaken point-in-time, source-provenance, or risk invariants.**
18. **Full automation is optional, not assumed to be the final destination.**

---

# 3. High-Level Roadmap

```text
PHASE 1
Deterministic engine
Risk engine
Lifecycle / pyramiding
Paper engine
Event-driven backtester
Integrity validation
        ↓
PHASE 1.5
Freeze + certify deterministic champion
        ↓
┌──────────────────────────────────────────────┐
│                                              │
▼                                              ▼
PHASE 2A                                  PHASE 2B
LIVE SHADOW                               ALPHA RESEARCH
Every valid signal                        Research dataset
Frozen strategy                           Attribution
True live PIT data                        Ablation
No capital                                Conditional analysis
│                                         Bullish Reset study
│                                         Regime interactions
│                                         Stability research
└──────────────────────┬───────────────────────┘
                       ↓
PHASE 3
CHALLENGER MODELS
Simple statistical models first
Champion vs challenger
                       ↓
PHASE 4
NEW-DATA EXPERIMENTS
Options
Cross-exchange derivatives
ETF flow surprise
Macro liquidity
Selected on-chain
                       ↓
PHASE 5
WALK-FORWARD / ROBUSTNESS / PROMOTION
                       ↓
PHASE 6
TINY-CAPITAL MANUAL LIVE TRADING
                       ↓
PHASE 7
META-MODEL / ENSEMBLE + PORTFOLIO OPTIMIZATION
                       ↓
PHASE 8
OPTIONAL SEMI-AUTOMATION
                       ↓
PHASE 9
FULL AUTOMATION ONLY IF JUSTIFIED
```

---

# 4. Phase 1.5 — Freeze and Certify the Deterministic Champion

Before adding ML, changing weights, or adding major datasets, freeze a benchmark.

Recommended frozen artifacts:

```text
strategy_v1.0
PRICE_SOURCE_POLICY_V1
SCORING_POLICY_V1
RISK_POLICY_V1
EXECUTION_MODEL_V1
```

The champion should be immutable except through the formal promotion process.

## 4.1 Required certification pack

Phase 1.5 should produce:

```text
walk-forward validation
source-sensitivity report
parameter robustness report
factor-overlap / de-nesting validation
score monotonicity report
setup-level performance
regime-level performance
Monte Carlo portfolio-risk analysis
golden historical scenarios
look-ahead-bias audit
risk-invariant audit
paper/backtest formula-parity audit
```

The purpose is to create an immutable answer to:

> What exactly did Phase 1 know, decide, and achieve?

Future research must compare against this fixed benchmark.

## 4.2 Phase 2 reference-price research

After `PRICE_SOURCE_POLICY_V1` is certified using the required Bitstamp,
Coinbase, and Bitfinex histories, create a separate research ticket for:

```text
BTC_REFERENCE_COMPOSITE_V1
```

The candidate should test a robust cross-venue reference and define source
eligibility, aggregation, outage behavior, provenance, versioning, and
price/indicator/decision/portfolio sensitivity. Coin Metrics may participate
as an optional institutional benchmark when historical entitlement is
available.

This research must compare against the frozen Phase 1 champion. It must not
silently replace the Phase 1 canonical source or splice provider histories, and
it requires a new policy version before any promotion.

---

# 5. Phase 2A — Live Shadow Operation

This should start **immediately after the Phase-1 champion is certified**.

Do not wait for ML or additional research.

## 5.1 Architecture

```text
LIVE MARKET DATA
        ↓
POINT-IN-TIME ALIGNMENT
        ↓
FROZEN PHASE-1 STRATEGY
        ↓
REGIME / SETUP / SCORES / RISK
        ↓
EVERY VALID SIGNAL
        ↓
AUTONOMOUS PAPER PORTFOLIO
        ↓
POSTGRESQL
```

The paper system must take **every valid model signal**.

Human discretion must not decide which model signals count.

This prevents selection bias.

## 5.2 Freeze every live decision

Persist at minimum:

```text
decision_time
observation_time
available_at
strategy_version
parameter_set_id
price_source_policy_version
regime
setup
direction
raw features
normalized features
component scores
entry conviction
hold score
add score
entry zone
invalidation
stop
R/R
risk budget
risk-at-stop
suggested size
action
reason codes
data-quality flags
market-state flags
```

Never reconstruct an old live decision using newer or revised data.

## 5.3 Live-shadow outcomes

Track:

```text
signal frequency
WATCH → ENTER conversion
missed entries
entry-zone touches
fill realism
slippage
fees
funding
stop behavior
MFE
MAE
time_to_MFE
time_to_MAE
R multiple
holding duration
adds
trims
exit reason
false setup frequency
data-quality failures
source disagreements
score-distribution drift
```

## 5.4 Main question

The first live-shadow question is not:

> Is the strategy profitable after two weeks?

It is:

> Does live behavior resemble the behavior implied by the historical backtest?

Examples:

```text
historical signal frequency vs live signal frequency
historical score distribution vs live score distribution
historical setup mix vs live setup mix
historical MAE/MFE distribution vs live MAE/MFE distribution
historical holding duration vs live holding duration
historical stop frequency vs live stop frequency
```

A major mismatch may indicate:

```text
data leakage
incorrect availability timestamps
provider differences
backtest execution assumptions
unmodeled live-data behavior
implementation drift
```

---

# 6. Phase 2B — Build the Alpha Research Dataset

The research dataset should become one of the most important assets in the project.

For every decision timestamp \(t\), store a point-in-time feature vector:

\[
X_t
\]

and keep future outcomes separately as:

\[
Y_{t,h}
\]

## 6.1 Suggested research row

```text
DECISION IDENTITY
decision_time
strategy_version
parameter_set
setup
regime
direction

RAW / NORMALIZED FEATURES
M4
M12
20W distance
52W-high distance
ETFNorm5
ETFNorm20
FlowAccel
SpotDominance
CVDSpread
FundingZ
OI growth
OI intensity
Basis
RV7
RV20
RV60
compression
orderliness
level strength
entry distance
support distance
structure features
macro features
on-chain features

COMPONENT SCORES
Trend
Flow
Positioning
Volatility
Structure

CONTEXT / FLAGS
Regime
STRESS
CROWDING
EUPHORIA
CAPITULATION
DATA_QUALITY_FAIL

DECISION
Entry Conviction
entry zone
invalidation
stop
R/R
risk budget
risk-at-stop
action

FORWARD LABELS
future_1w_return
future_2w_return
future_4w_return
future_8w_return
future_MFE
future_MAE
time_to_MFE
time_to_MAE
hit_2R_before_-1R
structural_thesis_success
```

## 6.2 Non-negotiable separation

```text
FEATURES AT t
-------------
Only information available at decision time

FUTURE OUTCOMES
---------------
Calculated after t
Never allowed into contemporaneous features
```

Forward labels must never contaminate feature generation.

---

# 7. Phase 2C — Baseline Attribution and Ablation

Do this before optimizing weights or adding many new data families.

## 7.1 Baseline strategies

Compare:

```text
FULL v1.x CHAMPION

Trend only

Trend + Structure

Trend + Flow

Trend + Flow + Structure

Trend + Flow + Positioning

Full model - Trend

Full model - Flow

Full model - Positioning

Full model - Volatility

Full model - Structure

Full model without selected vetoes
```

The purpose is not necessarily to create production strategies.

The purpose is to understand what drives the champion.

## 7.2 Metrics for every ablation

Track:

```text
trade count
trade overlap
entries added
entries removed
expectancy
average R
win rate
profit factor
Sharpe
Sortino
Calmar
max drawdown
MFE
MAE
time in market
turnover
holding period
conviction monotonicity
setup stability
regime stability
```

### Trade overlap matters

A component that marginally raises Sharpe but changes only a handful of trades may not provide robust incremental value.

Conversely, a component that materially changes entry selection and improves:

```text
expectancy
MAE
MFE
drawdown
```

may deserve substantial weight even if its standalone information coefficient is modest.

---

# 8. Phase 2D — Measure Information Before Optimizing Weights

Do not immediately search for:

```text
Trend = 27.5%
Flow = 22.5%
Positioning = 17.5%
...
```

First measure what the features actually tell us.

## 8.1 Conditional expectation

Examples:

\[
E[R_{4w} \mid Trend > 70]
\]

then:

\[
E[R_{4w} \mid Trend > 70,\ Flow > 70]
\]

then:

\[
E[R_{4w} \mid Trend > 70,\ Flow > 70,\ PositioningReset]
\]

Ask whether each added condition improves the distribution.

## 8.2 Information coefficients

For feature \(X\):

\[
IC_h = Corr(X_t,R_{t+h})
\]

Measure for:

```text
1 week
2 weeks
4 weeks
8 weeks
```

Use both:

```text
Pearson correlation
Spearman rank correlation
```

Do not rely on global full-sample values alone.

---

# 9. Phase 2E — Stability Through Time

A factor is more attractive when its relationship persists.

Compare:

\[
IC_{2018-2020}
\]

\[
IC_{2021-2022}
\]

\[
IC_{2023-2024}
\]

\[
IC_{2025-2026}
\]

Also condition by:

```text
bull
bear
neutral
high volatility
low volatility
pre-ETF
ETF era
setup type
```

A factor with modest but stable information content is often preferable to one
with a high full-sample average driven by a few isolated periods.

Example:

```text
Stable:
0.05
0.07
0.04
0.06
```

may be preferable to:

```text
Unstable:
-0.01
0.23
-0.03
0.15
```

---

# 10. Phase 2F — Regime-Dependent Research

The same feature should not automatically mean the same thing in every regime.

## 10.1 Example: funding

Suppose:

```text
Funding percentile = 85
```

### Early bull breakout

```text
Trend strengthening
Spot flow strong
OI moderate
Price near breakout
```

High funding may be acceptable.

### Late euphoric rally

```text
Price extended
OI extreme
Spot flow weakening
Basis elevated
```

The same funding level may indicate crowding and risk.

The research question becomes:

\[
E[R \mid Funding, Regime, Trend, OI, Flow]
\]

rather than:

\[
E[R \mid Funding]
\]

## 10.2 Example: volatility

Extreme volatility may be:

```text
negative for Bull Trend Continuation
```

but:

```text
part of the opportunity for Capitulation Reversal
```

Phase 2 should explicitly test setup-specific and regime-specific feature meaning.

---

# 11. Phase 2G — Bullish Reset Deep Research

Bullish Reset should be the first setup subjected to a full institutional alpha study.

This is not because it is assumed to be the best setup.

It is because it has a clear economic hypothesis:

```text
higher-timeframe bullish structure intact
+
meaningful correction
+
leverage flushed
+
funding normalized
+
OI deleveraged / stabilized
+
real-money demand returning
+
volatility normalizing
+
price reclaiming strong support
```

Conceptually:

\[
BullishStructure
\times
PositioningReset
\times
FlowRecovery
\times
GoodEntryLocation
\]

## 11.1 Research questions

Measure:

```text
What correction depth works best?
Does funding reset add independent information?
Does OI deleveraging add information after funding?
Does ETF flow acceleration matter?
Does absolute ETF flow matter?
Does support quality alter MAE?
Does reclaim confirmation improve expectancy?
How much does entry location affect R?
Does volatility normalization improve outcomes?
Does the interaction outperform individual factors?
```

## 11.2 Conditional example

Instead of:

> Funding below X is bullish.

Research:

> When BTC is in a 65+ bull regime, has corrected 10–20%, funding has moved from >80th percentile to <40th percentile, OI has fallen by at least one historical sigma, ETF-flow acceleration turns positive, and price reclaims weekly support — what is the distribution of 2-week and 4-week forward returns?

That is the kind of conditional relationship Phase 2 should seek.

---

# 12. Phase 2H — Separate Alpha from Trade Quality

This should be researched after the deterministic benchmark is stable.

Do not change the Phase-1 production architecture merely because this is conceptually attractive.

## 12.1 Alpha Score

Question:

> Is there directional opportunity?

Potential inputs:

```text
Trend
Flow
Positioning change
Momentum
Regime-conditioned interactions
selected macro / derivatives information
```

Conceptually:

\[
AlphaScore \approx E[FutureReturn \mid X_t]
\]

or:

\[
P(FavorableMove \mid X_t)
\]

## 12.2 Trade Quality Score

Question:

> Is this a good place and way to express that alpha?

Potential inputs:

```text
Structure
Entry location
Stop quality
Expected MAE
R/R
Volatility
Liquidity
Execution quality
```

Possible decision interpretation:

```text
Strong alpha + poor trade quality
→ WATCH / NO TRADE

Moderate alpha + exceptional asymmetric location
→ potentially valid

Strong alpha + strong trade quality
→ high-quality entry
```

This separation should be tested empirically before replacing Entry Conviction.

---

# 13. Phase 3 — Challenger Model Framework

The deterministic system remains the **champion**.

ML/statistical models are **challengers**.

```text
PRODUCTION CHAMPION
strategy_v1.0
        │
        └───────────────┐
                        ▼
                 Research Dataset
                        │
                        ▼
                  Challenger Models
                        │
            ┌───────────┼───────────┐
            ▼           ▼           ▼
      Rules v1.1     Model A     Model B
            │           │           │
            └───────────┼───────────┘
                        ▼
                Walk-forward comparison
                        │
                        ▼
                Manual promotion only
```

No challenger may modify the champion automatically.

---

# 14. First ML / Statistical Models

Do not start with neural networks.

Start with models that are easy to inspect:

```text
logistic regression
regularized logistic regression
linear regression
Elastic Net
gradient boosted trees
random forest as benchmark
```

Potential later challengers:

```text
XGBoost
LightGBM
probabilistic / Bayesian models
```

## 14.1 Suggested targets

Instead of asking:

> BUY or SELL Bitcoin?

ask:

\[
P(2R\ before\ -1R)
\]

or:

\[
E[R_{4w}]
\]

or:

\[
E[MFE]-\lambda E[MAE]
\]

or:

\[
P(StructuralThesisSuccess)
\]

The deterministic rules remain the setup/risk guardrails initially.

---

# 15. Raw Features vs Hand-Engineered Scores

Run a very important comparison.

## Model A

```text
RAW FEATURES
        ↓
same statistical model
```

## Model B

```text
HAND-ENGINEERED COMPONENT SCORES
        ↓
same statistical model
```

Interpretation:

### If raw features materially outperform

The scoring/compression layer may be destroying useful information.

### If component scores perform similarly

That is a positive result.

It suggests the deterministic feature engineering compresses information efficiently while preserving interpretability.

---

# 16. Interaction Research

The strongest alpha may come from interactions rather than standalone features.

Candidate interactions:

\[
Trend \times Flow
\]

\[
Flow \times Positioning
\]

\[
Positioning \times Structure
\]

\[
Trend \times Volatility
\]

and:

\[
FundingReset
\times
OIDeleveraging
\times
FlowImprovement
\]

The last interaction asks:

> Has leverage been flushed while genuine demand is beginning to return?

This may be especially relevant to Bullish Reset.

Interactions must be tested:

```text
globally
by regime
by setup
through time
out of sample
```

---

# 17. Phase 4 — New Institutional Data Experiments

Only add major new data after baseline attribution.

Every new dataset must prove:

```text
incremental information
out-of-sample stability
point-in-time availability
reliable history
reasonable acquisition cost
operational reliability
benefit greater than complexity cost
```

---

# 18. Options Data — Highest-Priority New Data Family

Candidate inputs:

```text
ATM implied volatility
IV term structure
25-delta call skew
25-delta put skew
risk reversals
put/call skew
options volume
options open interest
expiry concentration
large strike concentration
volatility risk premium
```

Potential core variable:

\[
VRP = IV - RV
\]

Changes in skew and term structure may matter more than static levels.

Example hypothesis:

```text
price holding major support
+
downside skew expands sharply
```

may contain different information from:

```text
price holding support
+
skew normalizes
```

Options data should not enter production simply because it appears institutional.

It must demonstrate incremental value.

---

# 19. Cross-Exchange Derivatives Research

Potential features:

```text
funding dispersion
OI dispersion
basis-curve shape
perp vs dated-futures divergence
liquidation intensity
spot/perp volume divergence
cross-exchange leverage concentration
```

Examples:

\[
Dispersion(Funding_i)
\]

\[
Dispersion(OI_i)
\]

The distribution of leverage across venues may contain information not visible in aggregate totals.

---

# 20. ETF Flow Surprise

Absolute ETF flow may not be the most informative representation.

Research:

\[
ETFSurprise_t =
ETFFlow_t -
E[ETFFlow_t \mid recent\ history]
\]

Example:

```text
+$300m
```

may be weak if recent daily flows were:

```text
+$800m
```

but meaningful if the market had experienced several weeks of outflows.

Potential research variants:

```text
flow surprise
flow acceleration
change in flow percentile
flow reversal
flow relative to recent volatility
flow relative to ETF AUM
```

---

# 21. Macro Liquidity and On-Chain Data

These should remain selective.

Potential macro/liquidity inputs:

```text
DXY
real yields
US 2Y
Nasdaq / risk proxy
global liquidity proxies
stablecoin liquidity
selected credit/risk measures
```

Potential on-chain inputs:

```text
SOPR
MVRV
realized profit/loss
short-term-holder realized price
exchange flows
selected holder-cost-basis metrics
```

No feature receives production status without incremental out-of-sample evidence.

---

# 22. Multiple-Hypothesis and Data-Mining Control

This becomes essential once research scales.

If testing:

```text
50 features
×
5 horizons
×
6 regimes
×
4 setups
×
many thresholds
```

false discoveries become inevitable.

The research framework should track every hypothesis tested.

## 22.1 Recommended protections

```text
discovery sample
validation sample
final out-of-sample / walk-forward confirmation
bootstrap confidence intervals
permutation tests
false-discovery-rate awareness
deflated Sharpe where applicable
parameter stability
multiple-regime confirmation
```

Core rule:

> No production promotion based only on the same sample used to discover the relationship.

Conceptually:

```text
DISCOVERY
Sample A
        ↓
VALIDATION
Sample B
        ↓
FINAL OOS / WALK-FORWARD
Sample C
```

---

# 23. Phase 5 — Champion / Challenger Promotion Process

Production must not self-modify.

```text
Champion strategy
        ↓
Live shadow + historical outcomes
        ↓
Research
        ↓
Candidate strategy version
        ↓
Walk-forward validation
        ↓
Robustness checks
        ↓
Independent review
        ↓
Manual promotion decision
```

## 23.1 Promotion criteria

A challenger should not be promoted merely because it has a higher Sharpe.

Evaluate:

```text
expectancy
average R
profit factor
Sharpe
Sortino
Calmar
max drawdown
trade count
turnover
time in market
stability through time
stability by regime
stability by setup
source sensitivity
parameter sensitivity
live-shadow consistency
complexity cost
data reliability
```

Prefer robust plateaus and persistent relationships over sharp historical optima.

---

# 24. Phase 6 — Tiny-Capital Manual Live Trading

Only after:

```text
Phase-1 champion certified
+
live shadow behaves plausibly
+
backtest/live implementation parity verified
+
risk invariants pass
```

Execution remains manual.

```text
Predictor
        ↓
Recommendation
        ↓
Human review
        ↓
Manual real trade
```

Maintain two separate portfolios:

```text
MODEL PAPER
takes every valid model signal

HUMAN ACTUAL
contains actual discretionary trades
```

Compare:

| Metric | Model Paper | Human Actual | Model + Human |
|---|---:|---:|---:|
| Trades | | | |
| Win rate | | | |
| Avg R | | | |
| Profit factor | | | |
| Max drawdown | | | |
| Sharpe | | | |
| Return/trade | | | |
| Missed winners | | | |
| Avoided losers | | | |

This can reveal whether human discretion adds or destroys value.

---

# 25. Phase 7 — Meta-Model / Ensemble

Later, stop thinking only in terms of one score.

Potential architecture:

```text
Deterministic setup engine
        +
Statistical expected-return model
        +
Setup-success probability
        +
Regime-specific model
        +
Trade-quality model
        +
Risk model
```

A future objective could resemble:

\[
ExpectedUtility
=
P(win)\times E[Winner]
-
P(loss)\times E[Loss]
\]

Example advisory output:

```text
Setup:
BULLISH RESET

Deterministic quality:
86 / 100

Statistical challenger:
P(2R before -1R): 68%
Expected 4w return: +7.4%
Expected MAE: -5.1%
Expected MFE: +16.2%

Historical setup expectancy:
+0.82R

Current regime percentile:
76th

ACTION:
ENTER INITIAL TRANCHE
```

The deterministic framework remains valuable because it supplies:

```text
structure
invalidation
risk
execution constraints
explainability
```

even if statistical models improve opportunity ranking.

---

# 26. Phase 7B — Portfolio Risk Optimization

After enough trades exist, stop guessing the best risk schedule.

Use historical/bootstrap/Monte Carlo distributions.

For trade outcomes:

\[
R_1,R_2,\ldots,R_n
\]

estimate:

```text
P(MaxDD > 10%)
P(MaxDD > 15%)
95th percentile losing streak
median ending NAV
5th percentile ending NAV
Calmar distribution
risk-of-ruin style metrics
```

Test risk schedules such as:

```text
0.25%
0.35%
0.50%
0.60%
0.75%
1.00%
```

The optimal improvement may come from better portfolio/risk sizing rather than better prediction.

---

# 27. Phase 8 — Optional Semi-Automation

Only after the decision engine and live process are trustworthy.

```text
Predictor
        ↓
Order proposal
        ↓
Human approval
        ↓
Exchange API
```

Possible automated functions:

```text
order placement
stop placement
stop movement
position reconciliation
fee tracking
fill tracking
portfolio-state persistence
```

The system still requires human approval to initiate a trade.

---

# 28. Phase 9 — Full Automation

Full autonomous execution is optional.

For a low-frequency system trading perhaps a few times per month, manual approval may impose very little operational cost.

Therefore:

> Full automation should occur only if evidence shows it creates a meaningful advantage.

A permanent end-state of:

```text
automated research
+
automated signal generation
+
automated risk calculation
+
automated paper trading
+
human-approved live execution
```

may be preferable.

---

# 29. Core Research Metrics

Do not judge the system primarily by prediction accuracy or win rate.

Primary metrics:

```text
expectancy
average R per trade
profit factor
Sharpe
Sortino
Calmar
max drawdown
average winner
average loser
time in market
turnover
number of trades
holding period
longest drawdown
longest losing streak
```

Research-specific metrics:

```text
information coefficient
rank information coefficient
conditional expectancy
MFE
MAE
time-to-MFE
time-to-MAE
factor correlation
rank correlation
factor concentration
effective rank
trade overlap
ablation impact
conviction monotonicity
regime stability
setup stability
parameter stability
source sensitivity
```

---

# 30. What the Research Process Is Trying to Discover

The likely strongest source of alpha is not simply:

```text
BTC above moving average
```

A more plausible mechanism is:

```text
market regime
×
positioning reset
×
real-money flow
×
structural location
```

In words:

> Higher-timeframe structure remains constructive, leveraged participants have been flushed, real capital begins returning, volatility is normalizing, and price offers an asymmetric entry near meaningful structure.

Bullish Reset is the first setup that most directly expresses this thesis.

Phase 2 should try to prove or disprove it.

---

# 31. Recommended Execution Order

```text
1. Finish Phase 1
2. Pass integrity / look-ahead / risk / execution audits
3. Freeze champion strategy_v1.0
4. Start live shadow portfolio immediately
5. Build alpha research dataset
6. Run baseline and ablation studies
7. Measure IC / conditional expectancy before weight optimization
8. Deep-study Bullish Reset
9. Test regime-dependent feature behavior
10. Test AlphaScore vs TradeQualityScore separation
11. Build simple challenger models
12. Compare raw features vs component scores
13. Test nonlinear interactions
14. Add options-data experiments
15. Add cross-exchange derivatives experiments
16. Research ETF-flow surprise
17. Add selected macro/on-chain experiments
18. Apply multiple-hypothesis controls
19. Run walk-forward champion/challenger validation
20. Promote only manually
21. Introduce tiny-capital manual live trading
22. Build empirical portfolio-risk optimization
23. Add semi-automation only if useful
24. Consider full automation only if justified
```

---

# 32. Final Operating Philosophy

The goal is not to create the most complicated Bitcoin model.

The goal is to create a trading process where every layer earns its place.

```text
Phase 1:
Build a coherent deterministic theory.

Phase 2:
Measure it, attack it, simplify it, and identify true conditional alpha.

Phase 3+:
Allow challengers and new data to compete against a frozen benchmark.

Live:
Promote only what survives point-in-time, out-of-sample, robustness, and risk validation.
```

The institutional mindset is:

> Better measurement, conditional analysis, robustness, and evidence are more valuable than more indicators.

And the most important long-term research question is:

> Which relationships remain useful after conditioning on regime, controlling for overlap, testing out of sample, and accounting for realistic execution and risk?

---

**Document Version:** 1.0  
**Purpose:** Post-Phase-1 alpha discovery, validation, champion/challenger research, and controlled progression toward live trading.  
**Primary Philosophy:** Improve evidence before complexity.  
**Production Rule:** No self-modification; all strategy changes require versioned research, validation, and manual promotion.  
**Live Progression:** Shadow first → tiny manual capital → optional semi-automation → full automation only if justified.
