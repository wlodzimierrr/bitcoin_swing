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


PROGRAM_TICKET = "POSTP1-001V2B"
OUTPUT_NAMESPACE = "prospective_evidence/trusted_acquisition_persistence_authority_v1"
PROTOCOL_FILENAME = "authority_definition.json"
REPORT_FILENAME = "TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1_REPORT.md"
FAILED_CALENDAR_AUTHORITY_SHA256 = "0524334396e529afbd057db25721b92c3074dd10205dd08be0946e512f99c855"
FINAL_CLASSIFICATION = "TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1_READY_FOR_XHIGH_REVIEW"


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
                "path; owner-only permissions"
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
            "atomicity": "VERIFY_COMPLETE_SIGNED_ENVELOPE_THEN_SINGLE_INSERT_IN_CALLER_TRANSACTION",
            "unsigned_authoritative_row": "IMPOSSIBLE_BY_SCHEMA_AND_WRITER_API",
            "signature_remains_mandatory_despite_database_privileges": True,
        }
    )


def creation_rehydration_and_failure_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "TRUSTED_ACQUISITION_CREATION_REHYDRATION_V1",
            "creation": "VERIFIED_HTTPS_PLUS_COLLECTOR_SIGNATURE_PLUS_COLLECTOR_ONLY_DB_INSERT",
            "rehydration": "DB_SELECT_PLUS_OFFLINE_SIGNATURE_AND_PAYLOAD_VERIFICATION",
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


def executable_semantic_manifest_contract() -> dict[str, Any]:
    owners = {
        "canonical_signed_message_builder": _trusted.canonical_signed_message,
        "payload_digest_builder": _trusted.sha256_json,
        "signature_verifier": _trusted.verify_envelope,
        "trusted_collector_signing_owner": _trusted.AcquisitionSigner.sign_payload,
        "trusted_collector_creation_owner": _calendar.collect_official_calendar,
        "rehydration_store_owner": _calendar.CalendarEvidenceStore.put,
        "postgres_append_owner": _persistence.PostgresTrustedAcquisitionAppender.append,
        "postgres_rehydration_owner": _persistence.rehydrate_verified_envelopes,
    }
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
    return _definition(
        {
            "contract_version": "TRUSTED_ACQUISITION_EXECUTABLE_SEMANTIC_MANIFEST_V1",
            "identity_method": "SHA-256 of normalized Python AST; locations excluded",
            "normalized_ast_sha256": _trusted.sha256_json(normalized),
            "owners": list(sorted(owners)),
            "runtime_change": "MOVES_MATERIAL_CHILD_AND_TOP_AUTHORITY_HASH",
            "cryptography_dependency": f"cryptography=={_trusted.CRYPTOGRAPHY_VERSION}",
        }
    )


_CHILD_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("signing_key_registry.json", "signing_key_registry_contract"),
    ("signed_message_contract.json", "signed_message_contract"),
    ("signed_payload_envelope_schema.json", "signed_payload_and_envelope_contract"),
    ("collector_creation_contract.json", "collector_creation_contract"),
    ("postgres_persistence_privileges.json", "persistence_and_privilege_contract"),
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
        "Verified collector execution now produces a canonical acquisition payload, an",
        "Ed25519 signature, and a collector-only PostgreSQL append. Replay loads the",
        "immutable envelope and verifies it offline against one frozen production public key.",
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
