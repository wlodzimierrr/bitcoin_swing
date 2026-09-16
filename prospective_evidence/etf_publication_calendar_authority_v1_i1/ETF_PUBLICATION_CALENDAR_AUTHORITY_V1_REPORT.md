# ETF_PUBLICATION_CALENDAR_AUTHORITY_V1

- Ticket: `POSTP1-001V2A-I1`
- Definition hash: `b499c6a4d1a8a6c25c6b108279831f26508742de97bdbcd57c7bee58e584e076`
- Status: `FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_CLOSURE_REVIEW`
- Classification: `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1_READY_FOR_FINAL_INTEGRATION_XHIGH_REVIEW`
- Material children: 13

## Frozen decision

ETF publication-date eligibility is the intersection of the NYSE Arca, Nasdaq,
and Cboe BZX U.S. equity session calendars. Regular and early-close sessions
are expected; full closures are not. Weekends are closed independently. Any
missing, invalid, or unresolved conflicting official evidence fails closed.

Calendar evidence is append-only. The trusted collector constructs the exact request,
performs verified HTTPS, validates every redirect hop, reads the response and timestamps
receipt itself. Admission requires a production envelope verified under the certified
trusted-persistence authority `02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772`. Unsigned/self-hashed
snapshots, provenance strings, and non-production envelopes are never authoritative.
Exact endpoint identity, full structural table traversal, semantic row census and complete
NYSE early-close prose are frozen and hash-bound; incomplete annual documents refuse.

Scientific `available_at` equals response receipt and acquisition time. PIT filtering
precedes revision replay, so future evidence cannot affect an earlier decision.
The normalized AST of every parser/reducer/adapter owner is hash-bound and runtime
replay refuses when the executable semantic identity differs.

## Retained official fixtures (2026-09-13)

Exact compressed response bytes and acquisition provenance for the NYSE, Nasdaq
Trader and Cboe official formats used for certification are retained under
`btc_predictor/tests/fixtures/etf_calendar/`. Their response SHA-256 values are
validated before parser extraction. No fixture is a prospective strategy observation.

## Failed lineage

The failed authorities `a1ceb66bc0f6b90066d3da123447ae6e7dd983047adf363790336bfb557db0b9`,
`b81c1702c65e1e042b7a2f948216305618fd21fabe2e629edc46376882b357af`, and
`0524334396e529afbd057db25721b92c3074dd10205dd08be0946e512f99c855` remain non-authoritative, non-certified,
unused, and preserved in their original artifact directories.

## Material child hashes

| child | definition hash |
| --- | --- |
| `authority_completion_semantic_diff` | `b413d3cd46038672a5ae61a5e97910f3d43c4d0cc206f9eb863620d877af87cc` |
| `common_session_rule` | `e731875421320560284d4727a30ab1f73e20af48fd1547b3203926464950fd8f` |
| `etf_feature_adapter_contract` | `640d3cb22a321d3e8d09affe9890a92251a36ee121b0c7303a61c7cc5e9df3b7` |
| `executable_semantic_manifest` | `a09a6d70eda9d2218929e72928962d9ea1aa8ca49e241235566838589feb08cf` |
| `http_acquisition_schema` | `0909d05779965e9d988b1c23fbd1632186a4e9e85a9575a5b1603806d59ff1e0` |
| `normalized_schedule_contract` | `bc84a9e73206382506bbca11b4d832a47ab573934fbdee5b3f00c4fd742fec87` |
| `official_source_profile_registry` | `734555c07f8ded9af9a768bf15ffdb0f8e2a0de051a279f1277f254d0df57afd` |
| `parser_format_census` | `d297effeb7cc647149088fd59ac17461a4764ec17f1950cdadf7df720459a498` |
| `pit_revision_rule` | `f2f1e748c64d9f1433e4d544fe844cdfa93524eac97d30c9428eadbbbaa6330f` |
| `source_parser_registry` | `f23f2d999c88768780ac3ea3b0d3daa1a5a15ea94715cf3d1196487ceaaee3e3` |
| `trusted_acquisition_persistence_dependency` | `38050555c36790839a021a926602a15de02cff2e7f0f9ef6e0df6e2d1e14f8af` |
| `trusted_https_collector_contract` | `4f4b4e551aa5476c478747d0c5fa61204e386ba773cef42f82f0ee8f3dcd5e9a` |
| `venue_session_record_schema` | `75f3948d61513cc4ec5cedb5227797fb52747e0e380e23eaaeae33544d43a29e` |

## Safety

No prospective observation was collected. The failed V2 corpus was not changed
or certified. POSTP1-003R3, POSTP1-004, collection, and BTC-019 remain blocked.
