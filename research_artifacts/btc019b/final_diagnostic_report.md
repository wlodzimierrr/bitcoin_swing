# BTC-019B External Gate Diagnostics

## Governance

- Diagnostic conclusion: `MIXED`
- `BTC_REFERENCE_COMPOSITE_V1`: `RESEARCH_INCONCLUSIVE` (unchanged)
- `PRICE_SOURCE_POLICY_V1`: unchanged
- BTC-019 recommendation: `IN PROGRESS`

## Degraded Reference

- Degraded bars: 286
- Contiguous episodes: 101
- Frozen degraded rate: 0.01087287104622871046228710462
- Economically material degraded bars: 0
- Economically material degraded episodes: 0
- Economically equivalent: 149 bars / 78 episodes
- Minor numeric difference only: 137 bars / 23 episodes

| Primary classification | Bars | Episodes | % hours | Structure | Stop | Trade/risk |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GENUINE_CROSS_MARKET_VOLATILITY | 104 | 41 | 0.003953771289537712895377128954 | 0 | 0 | 0 |
| ISOLATED_PROVIDER_OUTLIER | 45 | 33 | 0.001710766423357664233576642336 | 0 | 0 | 0 |
| MISSING_PROVIDER | 15 | 8 | 0.0005702554744525547445255474453 | 0 | 0 | 0 |
| PERSISTENT_PROVIDER_DISLOCATION | 106 | 12 | 0.004029805352798053527980535280 | 0 | 0 | 0 |
| PROVIDER_CLOSE_DISCONTINUITY | 16 | 7 | 0.0006082725060827250608272506083 | 0 | 0 | 0 |

The frozen degraded gate counts every usable quality warning equally. BTC-019B additionally measures episode-level structural and trade consequences; it does not replace or relax the failed V1 gate.

| Provider | Close outlier | High outlier | Low outlier | Missing | Agreeing cluster |
| --- | ---: | ---: | ---: | ---: | ---: |
| bitstamp | 15 | 15 | 13 | 0 | 256 |
| coinbase | 6 | 12 | 10 | 3 | 265 |
| bitfinex | 250 | 244 | 248 | 12 | 21 |

## Unusable Reference

- `REFERENCE_UNAVAILABLE`: 0
- unresolved `VENUE_DISAGREEMENT`: 3
- unavailable/disagreement rate: 0.0001140510948905109489051094891
- usable-reference rate: 0.9998859489051094890510948905

The three disagreement hours fall in the March 2020 capitulation week and April 2021 high week. Complete-period aggregation omits those weeks, which is analyzed separately from the 286 degraded-but-usable bars.

## Swing Diagnostics

| Metric | Disagreements | Denominator | Rate |
| --- | ---: | ---: | ---: |
| exact_timestamp | 4 | 33 | 0.1212121212121212121212121212 |
| within_1_week | 0 | 31 | 0 |
| within_2_week | 0 | 31 | 0 |
| structural_state | 2 | 33 | 0.06060606060606060606060606061 |
| stop_impact | 0 | 33 | 0 |
| trade_or_risk_material | 0 | 33 | 0 |

| Event | Side | Type | +/-1w | +/-2w | ATR distance | Classification | Stop | Trade/risk |
| --- | --- | --- | --- | --- | ---: | --- | --- | --- |
| 2021-04-12T00:00:00+00:00 | consensus_only | swing_high | True | True | 1.545837778721718236178111344 | STRUCTURAL_STATE_DIFFERENCE | False | False |
| 2021-04-05T00:00:00+00:00 | composite_only | swing_high | True | True | 1.545837778721718236178111344 | STRUCTURAL_STATE_DIFFERENCE | False | False |
| 2020-03-09T00:00:00+00:00 | consensus_only | swing_low | True | True | 0.7258615414843517994331603866 | MATERIAL_LEVEL_DIFFERENCE | False | False |
| 2020-03-16T00:00:00+00:00 | composite_only | swing_low | True | True | 0.7258615414843517994331603866 | MATERIAL_LEVEL_DIFFERENCE | False | False |

| ATR threshold | Material disagreements | Denominator | Rate |
| ---: | ---: | ---: | ---: |
| 0.10 | 4 | 33 | 0.1212121212121212121212121212 |
| 0.20 | 4 | 33 | 0.1212121212121212121212121212 |
| 0.30 | 4 | 33 | 0.1212121212121212121212121212 |
| 0.50 | 4 | 33 | 0.1212121212121212121212121212 |
| 1.00 | 2 | 33 | 0.06060606060606060606060606061 |

All four frozen exact disagreements remain recorded. The nearby-week and ATR grids are research-only diagnostics; they do not retroactively pass V1.

## Gate Assessment

The frozen total-frequency gate is not economically well specified as a standalone gate: it treats usable warnings with zero measured structural/trade effects like unusable reference failures. Preserve it for V1 and supplement, rather than retroactively replace, it.

Exact timestamps are too brittle as a standalone weekly-structure gate, but the failure exposed real omitted-week level and breakout state changes. Preserve the V1 result and require temporal, ATR, structural-state, and trade-risk diagnostics in a future version.

## V2 Research Recommendation

Propose a separately governed `BTC_REFERENCE_COMPOSITE_V2` study focused on quality-state semantics and complete-period behavior, while retaining median OHLC as the leading candidate. Predeclare degraded, unavailable, temporal swing-consensus, ATR-grid, structural-state, and trade-risk gates. Use only point-in-time inputs and prohibit unversioned fallback splicing.

The 2020-2025 history is inspected and cannot be pristine V2 out-of-sample evidence. The longest boundary-verified untouched common period is 2015-07-20 21:00 UTC through 2019-11-30 23:00 UTC. Freeze and measure its bulk completeness before opening it, then supplement it with future live-shadow validation.

## Limitations

Setup eligibility, entry eligibility, integrated stop placement, position sizing, and action generation are not wired into the BTC-019 research pipeline. BTC-019B reports those fields as unavailable instead of inventing results.
