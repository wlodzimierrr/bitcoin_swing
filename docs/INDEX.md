# Documentation Index

Start with [AGENTS.md](../AGENTS.md), this index, and
[CURRENT_STATE.md](CURRENT_STATE.md). Detailed authority remains in the
documents mapped below.

## Current / Authoritative

| Document | Purpose | Authority | When to read |
| --- | --- | --- | --- |
| [Structured Tickets v2.6](execution/bitcoin_swing_predictor_structured_tickets_v2_6.md) | Phase-1 ticket status, dependencies, execution order, acceptance criteria, and implementation/review notes | Authoritative Phase-1 execution roadmap | Read the exact ticket block; inspect dependency blocks and V2 order only as needed |
| [Rulebook v1.2](strategy/bitcoin_swing_predictor_rulebook_v1_2.md) | Strategy semantics and mathematics for v1.2 | Authoritative except scopes explicitly superseded by newer narrow versioned policies | Read only sections relevant to the ticket's formulas and invariants |
| [PRICE_SOURCE_POLICY_V1](policies/price_source_policy_v1.md) | Versioned empirical price-source evidence and conclusion | Authoritative for its explicitly defined V1 price-source-policy scope; newer than provisional Rulebook source language | Read for canonical/reference-source, provenance, fallback, or price-data work |

## Future Planning

| Document | Purpose | Authority | When to read |
| --- | --- | --- | --- |
| [Post-Phase-1 roadmap](roadmaps/bitcoin_swing_predictor_post_phase1_roadmap_v1.md) | Phase 1.5+ and post-Phase-1 planning | Future planning only; not current Phase-1 execution authority | Read when planning work beyond the current Phase-1 roadmap |

## Historical

| Document | Purpose | Authority | When to read |
| --- | --- | --- | --- |
| [Project Roadmap & Tickets v1](archive/bitcoin_swing_predictor_project_tickets_v1.md) | Original planning provenance | Historical only; never current dependency, status, execution, or strategy authority | Read only for explicit historical research |
| [Structured Tickets v1](archive/bitcoin_swing_predictor_project_tickets_structured_v1.md) | Original compact ticket provenance | Historical only; never current dependency, status, execution, or strategy authority | Read only for explicit historical research |

## Minimal Context for a Fresh Ticket Session

For normal ticket implementation or review, load only:

1. `/AGENTS.md`
2. `/docs/INDEX.md`
3. `/docs/CURRENT_STATE.md`
4. the exact `BTC-XXX` ticket block
5. direct dependency blocks when needed
6. relevant Rulebook sections
7. applicable narrow policy documents
8. related implementation and tests

Do not preload archived documents. Do not preload the full execution roadmap.
Do not preload the full Rulebook. Expand context only when evidence requires it.
