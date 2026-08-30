# BTC-129 Effective-Weight Report: v1.1 nested vs v1.2 de-nested

Contracts version: `SCORING_CONTRACTS_V1_2`  
Retired benchmark: `SCORING_CONTRACTS_V1_1`  
Parameter status: `PROVISIONAL_PENDING_BTC_185`

> This audit detects mechanical (structural) double-counting only: one leaf factor reaching a composite through more than one declared path. Natural empirical correlation between distinct components is expected, is not a defect, and is deliberately out of scope here.

## entry_conviction

| factor | v1.1 declared | v1.1 effective | v1.2 declared | v1.2 effective |
|---|---:|---:|---:|---:|
| confluence | — | 0.0150 | — | — |
| entry_location | — | 0.0375 | — | 0.0669643125 |
| flow | 0.20 | 0.2500 | 0.25 | 0.25 |
| level_strength | — | 0.0675 | — | 0.1205356875 |
| positioning | 0.15 | 0.1800 | 0.1875 | 0.1875 |
| rr_quality | — | 0.0300 | — | — |
| trend | 0.20 | 0.2900 | 0.25 | 0.25 |
| volatility | 0.10 | 0.1300 | 0.125 | 0.125 |

- v1.1 mechanically clean: **False** (double-counted: flow, positioning, trend, volatility)
- v1.2 mechanically clean: **True**
- v1.2 declared weight total: `1.0000`

## hold_score

| factor | v1.1 declared | v1.1 effective | v1.2 declared | v1.2 effective |
|---|---:|---:|---:|---:|
| confluence | — | 0.0100 | — | — |
| entry_location | — | 0.0250 | — | 0.0476190547619 |
| flow | 0.20 | 0.2625 | 0.2666667 | 0.2666667 |
| level_strength | — | 0.0450 | — | 0.0857142452381 |
| momentum_persistence | 0.10 | 0.10 | 0.1333333 | 0.1333333 |
| positioning | 0.15 | 0.1875 | 0.20 | 0.20 |
| rr_quality | — | 0.0200 | — | — |
| trend | 0.20 | 0.3125 | 0.2666667 | 0.2666667 |
| volatility | — | 0.0375 | — | — |

- v1.1 mechanically clean: **False** (double-counted: flow, positioning, trend)
- v1.2 mechanically clean: **True**
- v1.2 declared weight total: `1.0000000`

## add_score

| factor | v1.1 declared | v1.1 effective | v1.2 declared | v1.2 effective |
|---|---:|---:|---:|---:|
| confluence | — | 0.002000 | — | — |
| entry_location | — | 0.005000 | — | — |
| flow | 0.20 | 0.252500 | 0.25 | 0.25 |
| level_strength | — | 0.009000 | — | — |
| momentum | 0.10 | 0.10 | 0.125 | 0.125 |
| momentum_persistence | — | 0.0200 | — | — |
| new_structure | 0.25 | 0.25 | 0.3125 | 0.3125 |
| positioning | 0.15 | 0.187500 | 0.1875 | 0.1875 |
| risk_improvement | 0.10 | 0.10 | 0.125 | 0.125 |
| rr_quality | — | 0.004000 | — | — |
| trend | — | 0.062500 | — | — |
| volatility | — | 0.007500 | — | — |

- v1.1 mechanically clean: **False** (double-counted: flow, positioning, trend)
- v1.2 mechanically clean: **True**
- v1.2 declared weight total: `1.0000`
