# PROSPECTIVE_INTEGRATION_CORPUS_V2

- Program / ticket: `POSTP1-001V2` -- `EPIC X -- PROSPECTIVE INTEGRATION EVIDENCE`
- Definition hash: `488251df7bc1b49f801caa0dc28eb5224836574b154db9e4a70d4be670ec0b6d`
- Status: `FROZEN_PRE_DATA_REPLAY_COMPLETE_PARENT_V2_AWAITING_XHIGH_REVIEW`
- Classification: `PROSPECTIVE_INTEGRATION_CORPUS_V2_READY_FOR_XHIGH_REVIEW`
- Certification: `NOT_CERTIFIED_PENDING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW`
- Material children: 21

## Why V2 exists

`PROSPECTIVE_INTEGRATION_CORPUS_V1` (`8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7`) passed its sixth independent
exact-hash xHigh review and remains immutable historical certified
lineage. It is not modified in place and it is not invalid for any
semantics those reviews accepted. Its one limitation is narrow:

> REPLAY PROVENANCE INCOMPLETE FOR THE NEW SUFFICIENCY-AUTHORITY REQUIREMENT

V1 remains immutable historical certified lineage and is not invalid for any semantics its six reviews already accepted. It is insufficient only as the authoritative parent for the full transitive scientific replay that Stage-B sufficiency governance now requires.

The POSTP1-003R3 parent-completeness audit found three concrete gaps:
a warmup Boolean with no owner-specific history behind it, a portfolio
state chain that bound neither its predecessor record nor its producing
transition, and governance-authored conclusions filling both holes.
V2 closes them and changes nothing else.

## Semantic parity with V1

| change family | count |
| --- | --- |
| `acquisition_source_changes` | 0 |
| `decision_rule_changes` | 0 |
| `feature_formula_changes` | 0 |
| `metric_intent_changes` | 0 |
| `risk_changes` | 0 |
| `stage_b_direction_changes` | 0 |
| `stage_b_hard_role_changes` | 0 |
| `stage_b_threshold_changes` | 0 |
| `stop_event_definition_changes` | 0 |

Every count is recomputed on each build from the certified parent's own
gate authority, metric contracts, warmup rows and feature coverage; a
non-zero count refuses the build rather than freezing a drifted parent.

## Replay closure

- Stage-B metrics replayable: **8/8**
- Frozen features replayable: **33/33**
- Distinct owner classes: 12
- Warmup Boolean authoritative: **NO** -- warmup is a replayed
  derivation and a disagreeing cache refuses
- Slot evidence manifest: `PROSPECTIVE_SLOT_EVIDENCE_MANIFEST_V2`
- Owner history manifest: `PROSPECTIVE_OWNER_HISTORY_MANIFEST_V2`

## Portfolio graph

A transition references its prior state and never its resulting state; a state references its prior state and its producing transition. Identity therefore flows strictly backwards in time to a genesis with both references null, and no content hash can contain itself.

- Root lifecycle: Walk the verified predecessor/transition chain backwards from the state under evaluation until the ENTER transition that opened the currently open position after flat. That transition record's own content address is the root lifecycle identity. There is no governance-authored root-position SHA: the identity is a traversal result, and a forged root opening transition moves the chain and is refused by the state replay before the traversal reaches it.
- Active stop: A stop-event record proves membership by naming the control state record whose replayed lifecycle carries that exact active stop at the event time, inside the same root lifecycle episode. An asserted active_stop_identity establishes nothing on its own: the identity is re-derived from the graph and compared, and a stop belonging to another position moves the root and is refused.
- Exit / re-entry: A STOP_MOVE inside one position keeps the same root opening transition, because the chain reaches the same ENTER. An EXIT terminates the lifecycle, and the next ENTER can only occur on a new lifecycle, whose chain reaches a different ENTER. The two are therefore distinguishable by traversal alone, so a later sufficiency layer can count one root lifecycle unit per episode without a surrogate authority.

## Parent-completeness acceptance

A synthetic graph of 767 records and 33 owner-history
manifests derives every required blind fact from parent evidence alone.
None of the following is invented outside the parent graph:

- `active_stop_membership`
- `comparability Boolean`
- `control root SHA`
- `quality_state`
- `sizing-opportunity Boolean`
- `universe Boolean`
- `warmup Boolean`

## Inherited V1 children

- reused unchanged by hash: 14
- extended by a new V2 child: 9
- superseded for replay closure: 2
- V1 mutated: False

## Material child hashes

| child | definition hash |
| --- | --- |
| `active_stop_membership_contract` | `46157c0cd2cd0af54cfa511969f2b6dadf9b6366cba7c50824fe956aebfd77fd` |
| `collection_epoch_contract` | `11f3b03924fddf614bacd6f3887eeadf9ac8bd0a28fd5c2d1d6304e04097d745` |
| `data_schema_contract_v2` | `677e1c240ddc8f832af718acdd0445c2a9ed3e624a2e897101796ffa576b0ab3` |
| `decision_evaluability_contract` | `cbeb193cda8fb35e22e28d96eaacbcae6de07b87b2b4e31fe6479d405da01652` |
| `decision_observation_contract` | `a9a734b002f8f0df1ed5ab2a74beabecbb41912454a67544327fc266789d52e0` |
| `feature_replay_closure_matrix` | `009e5caf0bbe85bf2bc647efdb635ce6d5ea52a09fc3a1aee8d38017a3c46d21` |
| `inherited_v1_child_bindings` | `3ceacc17a8cb453b750431d5364d38cf8f0e1d4923e4ddc69bcde8588883ff7d` |
| `metric_replay_closure_matrix` | `6822762cecb701d0a79b2e68c603fdbabe34db3698bfa53030471985dd50b76d` |
| `owner_evaluability_census` | `bce172a6ef28596797ebda0d31c1cb314bdf323c5bbb5f287a19babed9982e65` |
| `owner_history_completeness_contract` | `e7f34efb702f2deed333473d0b659b2c1d071c295a272af6ab24ca4182645210` |
| `owner_history_manifest_contract` | `ee98e9d3893ef089e22f83c2360744a2521b8eabfa0aa577d78d6a019ce27e9e` |
| `parent_completeness_acceptance` | `7332ed64a87a5f39cf5e43d7fa4484ab708b2074ade90870f9aca6ef7fea0793` |
| `parent_replay_contract_registry` | `0621f330bf1a8724715f52f49075aa956f4e46d4ef9b6ff147187be901b6df8b` |
| `portfolio_state_contract` | `265bc0282fe683f4ee5f92461cd76bfc23e6c524c00d30fa2c4bfc9c00ef995e` |
| `portfolio_transition_contract` | `63322d43a52ecfdb7b07f1274f7d5eeaa08611f02d2130bce71504c2ad491520` |
| `portfolio_transition_replay_contract` | `f499f7747dc456b0d21b412b39c4c70c909001c9b3361db80b47c3b69a7f66a2` |
| `risk_opportunity_evidence_contract` | `5d278aff3a75cd2b54f73dbd94dfa555d4bafc2381d8a8f597dfa8ca72c8b97d` |
| `root_lifecycle_derivation_contract` | `a768ead194cd1431b27035763c17b1868ec7b89af03ed9bb2edc9df0a22bcbce` |
| `semantic_diff_v1_to_v2` | `83146e3063fd81824183e5637bcd5064475f62b029999dd56f6e6e01a8b3839e` |
| `slot_evidence_manifest_contract` | `287289d2d13850e2819b78cd74b78723ddee063969a948d613039eab8978154f` |
| `source_evidence_reuse_contract` | `fa35a4553e77020013bf360b5cf1bff0a545b03ce95e18d77ead5685feef235e` |

## Safety

- Collection authorized: False
- POSTP1-004 authorized: False
- New sufficiency governance issued here: False
- Qualifying observations collected: False
- Real Stage-B evaluated: False
- BTC-019 sealed data accessed: False
- Epic T modified: False

V2 qualifying prospective collection may begin only after this corpus passes an exact-hash independent xHigh review, sufficiency governance is reissued against the V2 hash and passes its own exact-hash review, and POSTP1-004 is implemented and passes its independent review.

