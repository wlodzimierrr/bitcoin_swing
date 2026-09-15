"""Frozen pre-data authority artifact for trusted acquisition persistence."""

from __future__ import annotations

import ast
import inspect
import json
import textwrap
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from btc_predictor.research import etf_publication_calendar as _calendar
from btc_predictor.research import trusted_acquisition as _trusted
from btc_predictor.research import trusted_acquisition_persistence as _persistence


PROGRAM_TICKET = "POSTP1-001V2B-R1"
OUTPUT_NAMESPACE = "prospective_evidence/trusted_acquisition_persistence_authority_v1_r1"
PROTOCOL_FILENAME = "authority_definition.json"
REPORT_FILENAME = "TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1_REPORT.md"
FAILED_CALENDAR_AUTHORITY_SHA256 = "0524334396e529afbd057db25721b92c3074dd10205dd08be0946e512f99c855"
FAILED_AUTHORITY_SHA256 = "c3619b7a72d2ee04247139f47130b995e8ef00514c6e2a736435ba4f2a223554"
FINAL_CLASSIFICATION = "TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1_READY_FOR_REPEAT_XHIGH_REVIEW"
FROZEN_AUTHORITY_DEFINITION_SHA256 = "240985bf042bc6b9910e39f6c5e170dc22a0385d93ef2f17fecc21c0adee7bd0"


class AuthorityArtifactError(ValueError):
    pass


def _definition(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["definition_sha256"] = _trusted.sha256_json(result)
    return result


def signing_key_registry_contract() -> dict[str, Any]:
    entry = _trusted.PRODUCTION_KEY_REGISTRY[_trusted.PRODUCTION_KEY_ID]
    return _definition(
        {
            "contract_version": "TRUSTED_ACQUISITION_SIGNING_KEY_REGISTRY_V1",
            "keys": [
                {
                    "key_id": entry.key_id,
                    "algorithm": entry.algorithm,
                    "public_key_base64": entry.public_key_base64,
                    "public_key_sha256": entry.public_key_sha256,
                    "authority_version": entry.authority_version,
                    "status": entry.status,
                }
            ],
            "production_key_count": 1,
            "dynamic_rotation": "FORBIDDEN",
            "replacement": "NEW_REVIEWED_TRUSTED_ACQUISITION_AUTHORITY_VERSION",
            "test_key_in_production_registry": False,
            "runtime_registry_representation": "FROZEN_VERIFICATION_KEY_PLUS_MAPPING_PROXY",
            "caller_trust_root_replacement": "FORBIDDEN",
        }
    )


def signed_message_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "TRUSTED_ACQUISITION_SIGNED_MESSAGE_V1",
            "signature_algorithm": _trusted.SIGNATURE_ALGORITHM,
            "domain_separator": _trusted.DOMAIN_SEPARATOR,
            "canonical_serialization": "RFC8259_SUBSET_SORTED_KEYS_COMPACT_ASCII_NO_NAN",
            "message_fields": [
                "authority_identity",
                "domain_separator",
                "schema_identity",
                "signed_payload_sha256",
                "signing_key_id",
            ],
            "schema_identity": _trusted.ENVELOPE_KIND,
            "authority_identity": _trusted.AUTHORITY_VERSION,
            "signature_excluded_from_payload_digest": True,
        }
    )


def signed_payload_and_envelope_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": _trusted.ENVELOPE_KIND,
            "signed_payload_required_origin_fields": [
                "record_kind",
                "schema_version",
                "source_profile_id",
                "source_authority_id",
                "venue_id",
                "request_url",
                "final_url",
                "redirect_chain",
                "http_method",
                "http_status",
                "response_content_type",
                "response_headers",
                "response_body_base64",
                "response_sha256",
                "trusted_collector_id",
                "tls_policy_id",
                "collector_semantic_sha256",
                "response_received_at",
                "acquired_at",
                "available_at",
                "parser_id",
                "parser_version",
                "source_format_version",
                "executable_semantic_sha256",
            ],
            "envelope_fields": [
                "record_kind",
                "schema_version",
                "authority_identity",
                "signed_payload",
                "signed_payload_sha256",
                "signing_key_id",
                "signature_algorithm",
                "signature",
                "envelope_sha256",
            ],
            "outer_hash": "SHA256_CANONICAL_ENVELOPE_EXCLUDING_ENVELOPE_SHA256",
            "verification": [
                "STRICT_SCHEMA",
                "INTEGER_SCHEMA_VERSION_EXCLUDING_BOOLEAN_AND_FLOAT",
                "CANONICAL_BASE64_REENCODE_EQUALITY",
                "VALID_ENVELOPE_HASH",
                "KNOWN_ACTIVE_FROZEN_KEY",
                "ED25519_ONLY",
                "RECOMPUTED_PAYLOAD_DIGEST",
                "DOMAIN_SEPARATED_SIGNATURE",
                "CORRECT_AUTHORITY_IDENTITY",
            ],
            "any_failure": "REFUSE",
        }
    )


def collector_creation_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "TRUSTED_ACQUISITION_COLLECTOR_CREATION_V1",
            "sequence": [
                "choose exact frozen source profile",
                "execute verified HTTPS collection",
                "validate endpoint redirects and HTTP response",
                "timestamp receipt",
                "validate parser and product scope",
                "build canonical acquisition payload",
                "compute payload digest",
                "sign domain-separated payload",
                "create signed envelope",
                "append signed envelope durably",
            ],
            "private_key_owner": "TRUSTED_COLLECTOR_PROCESS_ONLY",
            "private_key_provisioning": (
                "external secret storage or OS-protected deployment secret; explicit environment "
                "path; required O_NOFOLLOW single-open/fstat; regular file; effective-UID "
                "ownership; owner-only permissions; POSIX-with-O_NOFOLLOW required"
            ),
            "repository_private_key": "FORBIDDEN",
            "default_development_key": "FORBIDDEN",
            "fallback_key": "FORBIDDEN",
            "missing_or_mismatched_key": "REFUSE_NO_AUTHORITATIVE_ACQUISITION",
            "metadata_provenance_string_is_authority": False,
        }
    )


def persistence_and_privilege_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "TRUSTED_ACQUISITION_POSTGRES_PERSISTENCE_V1",
            "authoritative_table": "research.etf_calendar_trusted_acquisitions",
            "database": "PostgreSQL",
            "collector_role": "btc_calendar_collector_writer",
            "collector_privileges": ["SELECT", "INSERT"],
            "scientific_reader_role": "btc_predictor_scientific_reader",
            "scientific_reader_privileges": ["SELECT"],
            "forbidden_normal_workflow_privileges": ["UPDATE", "DELETE"],
            "public_privileges": [],
            "corrections": "NEW_SIGNED_ROWS_ONLY",
            "duplicate": "EXACT_ENVELOPE_IDEMPOTENT_BY_PRIMARY_KEY",
            "atomicity": (
                "VERIFY_PRODUCTION_SIGNATURE_THEN_OWNER_TRANSACTION_INSERT_COMMIT_THEN_NEW_"
                "CONNECTION_EXACT_ENVELOPE_READBACK"
            ),
            "authoritative_success": (
                "VALID_PRODUCTION_SIGNATURE_AND_COMMIT_ACKNOWLEDGED_AND_EXACT_POST_COMMIT_"
                "ENVELOPE_CONFIRMED"
            ),
            "caller_connection_as_durability_authority": False,
            "conflict_success": "ONLY_IF_EXISTING_EXACT_ENVELOPE_EQUALS_INTENDED",
            "commit_or_confirmation_ambiguity": "TRUSTED_ACQUISITION_COMMIT_UNCONFIRMED",
            "denormalized_columns": "QUERY_PROJECTIONS_CROSS_CHECKED_AGAINST_SIGNED_PAYLOAD",
            "unsigned_authoritative_row": "IMPOSSIBLE_BY_SCHEMA_AND_WRITER_API",
            "signature_remains_mandatory_despite_database_privileges": True,
        }
    )


def database_deployment_contract() -> dict[str, Any]:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "db/migrations/versions/0025_create_trusted_acquisition_persistence.py"
    )
    migration_ast = ast.dump(
        ast.parse(migration_path.read_text(encoding="utf-8")),
        annotate_fields=True,
        include_attributes=False,
    )
    return _definition(
        {
            "contract_version": "TRUSTED_ACQUISITION_POSTGRES_ROLE_BOOTSTRAP_V1",
            "bootstrap_owner": "ALEMBIC_MIGRATION_0025_BEFORE_GRANTS",
            "roles": {
                "btc_calendar_collector_writer": [
                    "NOLOGIN", "NOSUPERUSER", "NOCREATEDB", "NOCREATEROLE",
                    "NOREPLICATION", "NOBYPASSRLS",
                ],
                "btc_predictor_scientific_reader": [
                    "NOLOGIN", "NOSUPERUSER", "NOCREATEDB", "NOCREATEROLE",
                    "NOREPLICATION", "NOBYPASSRLS",
                ],
            },
            "existing_incompatible_role": "FAIL_CLOSED",
            "authority_role_membership_in_another_role": "FAIL_CLOSED",
            "public_schema_create": False,
            "collector_schema_create": False,
            "reader_schema_create": False,
            "application_login_membership": "DEPLOYMENT_SPECIFIC_OUTSIDE_SCIENTIFIC_EVIDENCE",
            "infrastructure_trust_authorities": ["DATABASE_TABLE_OWNER", "CLUSTER_SUPERUSER"],
            "normal_credentials": "NEITHER_SUPERUSER_NOR_TABLE_OWNER",
            "dba_compromise_defended": False,
            "migration_normalized_ast_sha256": _trusted.sha256_json(migration_ast),
        }
    )


def creation_rehydration_and_failure_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "TRUSTED_ACQUISITION_CREATION_REHYDRATION_V1",
            "creation": (
                "VERIFIED_HTTPS_PLUS_INTERNAL_PRODUCTION_SIGNER_PLUS_INTERNALLY_OWNED_"
                "COMMIT_CONFIRMED_POSTGRES_APPEND"
            ),
            "rehydration": "DB_SELECT_PLUS_FIXED_PRODUCTION_KEY_SIGNATURE_AND_PROJECTION_VERIFICATION",
            "rehydration_private_key_required": False,
            "in_memory_store": "TEST_OR_REPLAY_CACHE_NOT_PRODUCTION_ORIGIN_BOUNDARY",
            "in_memory_source_admission": "SIGNED_ENVELOPE_ONLY_AFTER_VERIFICATION",
            "unsigned_mapping": "REFUSE",
            "failures_producing_no_authoritative_acquisition": [
                "HTTPS_FAILURE",
                "PARSER_FAILURE",
                "RECEIPT_CLOCK_FAILURE",
                "PRIVATE_KEY_UNAVAILABLE",
                "SIGNATURE_FAILURE",
                "DATABASE_APPEND_FAILURE",
                "SIGNATURE_VERIFICATION_FAILURE",
            ],
            "key_compromise_or_rotation": "STOP_COLLECTION_AND_ISSUE_NEW_REVIEWED_AUTHORITY_VERSION",
            "historical_signature_rule": "REPLAY_UNDER_FROZEN_KEY_AUTHORITY_UNLESS_FUTURE_GOVERNANCE_REVOKES",
            "production_signer_injection": "FORBIDDEN",
            "production_appender_injection": "FORBIDDEN",
            "production_registry_injection": "FORBIDDEN",
        }
    )


def threat_and_security_boundary_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "TRUSTED_ACQUISITION_THREAT_MODEL_V1",
            "defends_against": [
                "APPLICATION_OR_REPLAY_MANUFACTURE",
                "FIXTURE_MANUFACTURE",
                "MANUAL_JSON_EDITING",
                "SELF_HASH_RECOMPUTATION",
                "PROVENANCE_STRING_COPYING",
                "SEMANTIC_HASH_COPYING",
                "DATABASE_READER_FABRICATION",
            ],
            "excluded": ["TRUSTED_COLLECTOR_HOST_OR_PRIVATE_KEY_COMPROMISE"],
            "claim": (
                "Ed25519 proves possession of the trusted collector signing key for the exact "
                "persisted payload. Combined with frozen verified-HTTPS collector code and "
                "exclusive key availability, it establishes the project source-origin boundary."
            ),
            "independent_third_party_tls_transcript_claimed": False,
        }
    )


def _executable_semantic_owners() -> dict[str, Any]:
    return {
        "canonical_json_bytes": _trusted.canonical_json_bytes,
        "sha256_json": _trusted.sha256_json,
        "canonical_signed_message": _trusted.canonical_signed_message,
        "sha256_identity_validator": _trusted._is_sha256,
        "public_key_decoder": _trusted._decode_public_key,
        "external_private_key_loader": _trusted.AcquisitionSigner.from_external_secret,
        "sign_payload": _trusted.AcquisitionSigner.sign_payload,
        "private_public_registry_match": _trusted.AcquisitionSigner._assert_registry_match,
        "generic_test_only_verifier": _trusted._verify_envelope_against_key_non_authoritative_test_only,
        "production_envelope_verifier": _trusted.verify_production_envelope,
        "runtime_attestation_owner": _trusted._assert_runtime_semantics,
        "frozen_runtime_attestation": assert_frozen_runtime_semantics,
        "production_store_admission": _calendar.CalendarEvidenceStore.put,
        "production_store_sealing": _calendar.CalendarEvidenceStore.__init_subclass__,
        "production_collection_orchestration": _calendar.collect_official_calendar,
        "collection_logic_closure": _calendar._collect_official_calendar_non_authoritative_test_only,
        "production_persistence_facade": _persistence.PostgresTrustedAcquisitionAppender.append,
        "production_committed_persistence": _persistence.append_production_envelope_committed,
        "transaction_commit_confirmation": _persistence._append_with_owned_engine_non_authoritative_test_only,
        "persistence_value_projection": _persistence._persistence_values,
        "authoritative_envelope_query": _persistence.authoritative_envelope_query,
        "production_rehydration": _persistence.rehydrate_verified_envelopes,
        "denormalized_projection_check": _persistence._assert_projection_equality,
        "persistence_utc_validator": _persistence._utc,
    }


def current_executable_semantic_sha256() -> str:
    owners = _executable_semantic_owners()
    normalized = [
        {
            "owner": name,
            "ast": ast.dump(
                ast.parse(textwrap.dedent(inspect.getsource(owner))),
                annotate_fields=True,
                include_attributes=False,
            ),
        }
        for name, owner in sorted(owners.items())
    ]
    normalized.append(
        {
            "owner": "calendar_collection_material_helper_closure",
            "semantic_sha256": _calendar._semantic_ast_sha256(),
        }
    )
    return _trusted.sha256_json(normalized)


def executable_semantic_manifest_contract() -> dict[str, Any]:
    owners = _executable_semantic_owners()
    return _definition(
        {
            "contract_version": "TRUSTED_ACQUISITION_EXECUTABLE_SEMANTIC_MANIFEST_V1",
            "identity_method": "SHA-256 of normalized Python AST; locations excluded",
            "normalized_ast_sha256": current_executable_semantic_sha256(),
            "owners": list(sorted(owners)),
            "material_helper_closures": ["ETF_CALENDAR_EXECUTABLE_SEMANTIC_MANIFEST_V1"],
            "runtime_change": "MOVES_MATERIAL_CHILD_AND_TOP_AUTHORITY_HASH_AND_REFUSES_OLD_ARTIFACT",
            "runtime_expected_identity_source": (
                "PERSISTED_PARENT_BOUND_EXECUTABLE_SEMANTIC_MANIFEST_NOT_DYNAMIC_RUNTIME"
            ),
            "cryptography_dependency": f"cryptography=={_trusted.CRYPTOGRAPHY_VERSION}",
        }
    )


_CHILD_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("signing_key_registry.json", "signing_key_registry_contract"),
    ("signed_message_contract.json", "signed_message_contract"),
    ("signed_payload_envelope_schema.json", "signed_payload_and_envelope_contract"),
    ("collector_creation_contract.json", "collector_creation_contract"),
    ("postgres_persistence_privileges.json", "persistence_and_privilege_contract"),
    ("postgres_role_bootstrap.json", "database_deployment_contract"),
    ("creation_rehydration_failure_contract.json", "creation_rehydration_and_failure_contract"),
    ("threat_security_boundary.json", "threat_and_security_boundary_contract"),
    ("executable_semantic_manifest.json", "executable_semantic_manifest_contract"),
)


def _children() -> dict[str, dict[str, Any]]:
    return {
        filename.removesuffix(".json"): globals()[builder]()
        for filename, builder in _CHILD_ARTIFACTS
    }


def authority_definition() -> dict[str, Any]:
    children = _children()
    return _definition(
        {
            "authority_version": _trusted.AUTHORITY_VERSION,
            "program_ticket": PROGRAM_TICKET,
            "workstream": "EPIC X — PROSPECTIVE INTEGRATION EVIDENCE",
            "status": "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW",
            "final_classification": FINAL_CLASSIFICATION,
            "certified": False,
            "required_review": "INDEPENDENT_EXACT_HASH_XHIGH_REVIEW",
            "material_child_count": len(children),
            "child_definition_sha256": {
                name: child["definition_sha256"] for name, child in children.items()
            },
            "blocked_calendar_authority": FAILED_CALENDAR_AUTHORITY_SHA256,
            "failed_authority_retained_non_authoritative": FAILED_AUTHORITY_SHA256,
            "failed_authority_observations": 0,
            "failed_authority_superseded_before_use": True,
            "clock_semantics": "response_received_at == acquired_at == available_at",
            "https_semantics_changed": False,
            "parser_semantics_changed": False,
            "common_session_semantics_changed": False,
            "etf_science_changed": False,
            "safety": {
                "prospective_observations": 0,
                "real_stage_b_evaluation": False,
                "etf_calendar_authority_certified": False,
                "postp1_001v2r1_blocked": True,
                "postp1_003r3_blocked": True,
                "postp1_004_blocked": True,
                "collection_authorized": False,
                "btc019_untouched": True,
                "epic_t_unchanged": True,
            },
        }
    )


def verify_authority_definition(persisted: Mapping[str, Any]) -> None:
    if dict(persisted) != authority_definition():
        raise AuthorityArtifactError("persisted authority does not reproduce")
    _verify_digest(persisted)


def assert_frozen_runtime_semantics() -> None:
    """Compare current material runtime owners with the parent-bound frozen identity."""

    root = Path(__file__).resolve().parents[2] / OUTPUT_NAMESPACE
    try:
        parent = json.loads((root / PROTOCOL_FILENAME).read_text(encoding="ascii"))
        manifest = json.loads(
            (root / "executable_semantic_manifest.json").read_text(encoding="ascii")
        )
    except (OSError, json.JSONDecodeError) as error:
        raise _trusted.TrustedAcquisitionError(
            "frozen executable semantic authority is unavailable"
        ) from error
    try:
        _verify_digest(parent)
        _verify_digest(manifest)
    except AuthorityArtifactError as error:
        raise _trusted.TrustedAcquisitionError(
            "frozen executable semantic authority is invalid"
        ) from error
    if parent.get("definition_sha256") != FROZEN_AUTHORITY_DEFINITION_SHA256:
        raise _trusted.TrustedAcquisitionError(
            "trusted-acquisition authority identity is not the frozen expected identity"
        )
    expected_child = parent.get("child_definition_sha256", {}).get(
        "executable_semantic_manifest"
    )
    if expected_child != manifest.get("definition_sha256"):
        raise _trusted.TrustedAcquisitionError(
            "executable semantic manifest is not parent-bound"
        )
    if manifest.get("normalized_ast_sha256") != current_executable_semantic_sha256():
        raise _trusted.TrustedAcquisitionError(
            "runtime executable semantic identity differs from frozen authority"
        )


def _verify_digest(payload: Mapping[str, Any]) -> None:
    row = dict(payload)
    declared = row.pop("definition_sha256", None)
    if not isinstance(declared, str) or _trusted.sha256_json(row) != declared:
        raise AuthorityArtifactError("definition SHA-256 does not recompute")


def _report(protocol: Mapping[str, Any]) -> str:
    lines = [
        f"# {_trusted.AUTHORITY_VERSION}",
        "",
        f"- Ticket: `{PROGRAM_TICKET}`",
        f"- Definition hash: `{protocol['definition_sha256']}`",
        f"- Classification: `{FINAL_CLASSIFICATION}`",
        f"- Material children: {protocol['material_child_count']}",
        "",
        "Verified collector execution now produces a canonical acquisition payload and an",
        "Ed25519 signature. The production persistence owner reports success only after its",
        "PostgreSQL commit and independent exact-envelope readback. Replay verifies the",
        "immutable envelope against one frozen production public key and cross-checks every",
        "denormalized projection.",
        "Self-hashes and provenance strings are descriptive and cannot establish origin.",
        "",
        "The signature proves possession of the collector key for the exact payload; this",
        "does not claim an independent third-party cryptographic TLS transcript.",
        "",
        "## Material child hashes",
        "",
        "| child | definition hash |",
        "| --- | --- |",
    ]
    for child, digest in sorted(protocol["child_definition_sha256"].items()):
        lines.append(f"| `{child}` | `{digest}` |")
    lines += [
        "",
        "## Safety",
        "",
        "No prospective observations were collected. Calendar certification, V2R1,",
        "POSTP1-003R3, POSTP1-004, and collection remain blocked pending review and the",
        "explicit downstream sequence. BTC-019 and Epic T are unchanged.",
        "",
    ]
    return "\n".join(lines)


def write_artifacts(output_dir: Path) -> dict[str, Any]:
    protocol = authority_definition()
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {PROTOCOL_FILENAME: protocol}
    payloads.update(
        {filename: globals()[builder]() for filename, builder in _CHILD_ARTIFACTS}
    )
    for filename, payload in payloads.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
        )
    (output_dir / REPORT_FILENAME).write_text(_report(protocol), encoding="utf-8")
    return protocol


def restore_artifacts(output_dir: Path) -> dict[str, Any]:
    protocol = json.loads((output_dir / PROTOCOL_FILENAME).read_text(encoding="ascii"))
    verify_authority_definition(protocol)
    for filename, builder in _CHILD_ARTIFACTS:
        persisted = json.loads((output_dir / filename).read_text(encoding="ascii"))
        expected = globals()[builder]()
        if persisted != expected:
            raise AuthorityArtifactError(f"persisted {filename} does not reproduce")
        _verify_digest(persisted)
    if (output_dir / REPORT_FILENAME).read_text(encoding="utf-8") != _report(protocol):
        raise AuthorityArtifactError("persisted report does not reproduce")
    return protocol


def main() -> None:  # pragma: no cover
    root = Path(__file__).resolve().parents[2]
    print(write_artifacts(root / OUTPUT_NAMESPACE)["definition_sha256"])


if __name__ == "__main__":  # pragma: no cover
    main()
