"""POSTP1-001V2B hostile cryptographic and persistence regressions."""

from __future__ import annotations

import base64
import copy
import gzip
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from btc_predictor.db import render_upgrade_sql
from btc_predictor.research import etf_publication_calendar as calendar
from btc_predictor.research import trusted_acquisition as trusted
from btc_predictor.research import trusted_acquisition_authority as authority
from btc_predictor.research.trusted_acquisition_persistence import (
    PostgresTrustedAcquisitionAppender,
    rehydrate_verified_envelopes,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = Path(__file__).with_name("fixtures") / "etf_calendar"
PROVENANCE = json.loads((FIXTURE_DIR / "official_fixture_provenance.json").read_text())
ACQUIRED = datetime.fromisoformat(PROVENANCE["acquired_at"])
TEST_PRIVATE_BYTES = bytes(range(32))
TEST_SIGNER = trusted.AcquisitionSigner(
    Ed25519PrivateKey.from_private_bytes(TEST_PRIVATE_BYTES),
    "TEST_ONLY_ED25519_V1",
)
TEST_REGISTRY = {TEST_SIGNER.key_id: TEST_SIGNER.verification_key()}


def fixture_bytes() -> bytes:
    metadata = PROVENANCE["fixtures"]["NASDAQ"]
    encoded = (FIXTURE_DIR / metadata["fixture"]).read_bytes()
    return gzip.decompress(base64.b64decode(encoded))


class MemoryAppender:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.envelopes: list[dict] = []

    def append(self, envelope: dict) -> str:
        if self.fail:
            raise trusted.TrustedAcquisitionError("database append failed")
        trusted.verify_envelope(envelope, registry=TEST_REGISTRY)
        self.envelopes.append(copy.deepcopy(envelope))
        return envelope["envelope_sha256"]


def signed_envelope(*, appender: MemoryAppender | None = None) -> dict:
    metadata = PROVENANCE["fixtures"]["NASDAQ"]
    observation = {
        "request_url": metadata["request_url"],
        "final_url": metadata["final_url"],
        "redirect_chain": (),
        "http_status": 200,
        "response_headers": {"Content-Type": metadata["response_content_type"]},
        "response_bytes": fixture_bytes(),
    }
    executable_sha = calendar._semantic_ast_sha256()
    with (
        patch.object(calendar, "_perform_verified_https_get", return_value=observation),
        patch.object(calendar, "_semantic_ast_sha256", return_value=executable_sha),
    ):
        return calendar.collect_official_calendar(
            metadata["source_profile_id"],
            lambda: ACQUIRED,
            signer=TEST_SIGNER,
            appender=appender or MemoryAppender(),
        )


def recompute_unsigned_hashes(envelope: dict) -> dict:
    changed = copy.deepcopy(envelope)
    payload = changed["signed_payload"]
    payload.pop(calendar.RECORD_DIGEST_FIELD, None)
    payload[calendar.RECORD_DIGEST_FIELD] = calendar._digest(payload)
    changed["signed_payload_sha256"] = trusted.sha256_json(payload)
    changed.pop("envelope_sha256", None)
    changed["envelope_sha256"] = trusted.sha256_json(changed)
    return changed


def test_production_registry_is_one_frozen_ed25519_public_key() -> None:
    assert list(trusted.PRODUCTION_KEY_REGISTRY) == [trusted.PRODUCTION_KEY_ID]
    entry = trusted.PRODUCTION_KEY_REGISTRY[trusted.PRODUCTION_KEY_ID]
    public = base64.b64decode(entry.public_key_base64, validate=True)
    assert entry.algorithm == "Ed25519"
    assert entry.status == "ACTIVE"
    assert hashlib.sha256(public).hexdigest() == entry.public_key_sha256
    assert TEST_SIGNER.key_id not in trusted.PRODUCTION_KEY_REGISTRY
    assert TEST_SIGNER.verification_key().public_key_base64 != entry.public_key_base64


def test_missing_production_private_key_has_no_default_or_fallback() -> None:
    with pytest.raises(trusted.TrustedAcquisitionError, match="unavailable"):
        trusted.AcquisitionSigner.from_external_secret(environ={})


def test_deterministic_ed25519_compatibility_vector() -> None:
    first = TEST_SIGNER.sign_payload({"vector": "POSTP1-001V2B", "n": 1})
    second = TEST_SIGNER.sign_payload({"n": 1, "vector": "POSTP1-001V2B"})
    assert first == second
    assert first["signature"] == (
        "VmFs58MvkGMOlgBeJqS3PPEKE4pjVqxid4hmL1MrWJM8fYVIlnCvnATJ11GQK76ZlAv2B/"
        "n9F14ZAE7gkCh9BQ=="
    )
    assert trusted.verify_envelope(first, registry=TEST_REGISTRY) == {
        "n": 1,
        "vector": "POSTP1-001V2B",
    }


def test_self_hashed_unsigned_forgery_and_copied_trust_fields_refused() -> None:
    forged = signed_envelope()["signed_payload"]
    assert forged["acquisition_provenance"] == calendar.TRUSTED_ACQUISITION_PROVENANCE
    assert forged["collector_semantic_sha256"] == calendar._semantic_ast_sha256()
    with pytest.raises(calendar.EtfCalendarAuthorityError, match="unsigned acquisition refused"):
        calendar.CalendarEvidenceStore().put(forged)


def test_test_key_and_random_signature_are_refused_by_production_registry() -> None:
    envelope = signed_envelope()
    with pytest.raises(trusted.TrustedAcquisitionError, match="not frozen"):
        trusted.verify_envelope(envelope)
    random_signature = copy.deepcopy(envelope)
    random_signature["signature"] = base64.b64encode(bytes(64)).decode("ascii")
    random_signature.pop("envelope_sha256")
    random_signature["envelope_sha256"] = trusted.sha256_json(random_signature)
    with pytest.raises(trusted.TrustedAcquisitionError, match="signature is invalid"):
        trusted.verify_envelope(random_signature, registry=TEST_REGISTRY)


@pytest.mark.parametrize(
    "field",
    [
        "response_body_base64",
        "response_sha256",
        "request_url",
        "redirect_chain",
        "venue_id",
        "source_profile_id",
        "available_at",
        "collector_semantic_sha256",
        "parser_id",
    ],
)
def test_payload_tampering_with_all_self_hashes_recomputed_still_refuses(field: str) -> None:
    envelope = signed_envelope()
    payload = envelope["signed_payload"]
    if field == "response_body_base64":
        body = fixture_bytes() + b" "
        payload[field] = base64.b64encode(body).decode("ascii")
        payload["response_sha256"] = hashlib.sha256(body).hexdigest()
    elif field == "response_sha256":
        payload[field] = "f" * 64
    elif field == "redirect_chain":
        payload[field] = [payload["final_url"]]
    elif field == "available_at":
        payload[field] = "2020-01-01T00:00:00+00:00"
    else:
        payload[field] = f"FORGED_{payload[field]}"
    forged = recompute_unsigned_hashes(envelope)
    with pytest.raises(calendar.EtfCalendarAuthorityError, match="signature is invalid"):
        calendar.CalendarEvidenceStore(key_registry=TEST_REGISTRY).put(forged)


def test_signature_substitution_and_key_id_substitution_refuse() -> None:
    first = signed_envelope()
    second = copy.deepcopy(first)
    second["signed_payload"]["published_at"] = ACQUIRED.isoformat()
    second = recompute_unsigned_hashes(second)
    second["signature"] = first["signature"]
    second.pop("envelope_sha256")
    second["envelope_sha256"] = trusted.sha256_json(second)
    with pytest.raises(trusted.TrustedAcquisitionError, match="signature is invalid"):
        trusted.verify_envelope(second, registry=TEST_REGISTRY)

    substituted = copy.deepcopy(first)
    substituted["signing_key_id"] = "TEST_ONLY_OTHER_KEY"
    substituted.pop("envelope_sha256")
    substituted["envelope_sha256"] = trusted.sha256_json(substituted)
    with pytest.raises(trusted.TrustedAcquisitionError, match="not frozen"):
        trusted.verify_envelope(substituted, registry=TEST_REGISTRY)


def test_valid_signed_envelope_rehydrates_and_calendar_replay_succeeds() -> None:
    envelope = signed_envelope()
    rows = [
        {
            "envelope_sha256": envelope["envelope_sha256"],
            "signed_payload": envelope["signed_payload"],
            "signed_payload_sha256": envelope["signed_payload_sha256"],
            "signing_key_id": envelope["signing_key_id"],
            "signature_algorithm": envelope["signature_algorithm"],
            "signature": envelope["signature"],
        }
    ]
    rehydrated = rehydrate_verified_envelopes(rows, registry=TEST_REGISTRY)
    store = calendar.CalendarEvidenceStore(rehydrated, key_registry=TEST_REGISTRY)
    source_id = envelope["signed_payload"][calendar.RECORD_DIGEST_FIELD]
    assert store.get(source_id) == envelope["signed_payload"]
    schedule = calendar.derive_normalized_schedule_from_official_source(
        store, acquisition_record_sha256=source_id
    )
    assert schedule["venue_id"] == "NASDAQ"


def test_fresh_process_offline_signature_verification(tmp_path: Path) -> None:
    envelope = signed_envelope()
    path = tmp_path / "envelope.json"
    path.write_text(json.dumps(envelope), encoding="ascii")
    entry = TEST_REGISTRY[TEST_SIGNER.key_id]
    script = """
import json, sys
from pathlib import Path
from btc_predictor.research.trusted_acquisition import VerificationKey, verify_envelope
row=json.loads(Path(sys.argv[1]).read_text())
key=VerificationKey(**json.loads(sys.argv[2]))
payload=verify_envelope(row, registry={key.key_id:key})
print(payload['response_sha256'])
"""
    encoded_entry = json.dumps(entry.__dict__)
    completed = subprocess.run(
        [sys.executable, "-c", script, str(path), encoded_entry],
        cwd=ROOT,
        env=dict(os.environ, PYTHONPATH=str(ROOT)),
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == envelope["signed_payload"]["response_sha256"]


def test_collector_append_failure_creates_no_returned_authority() -> None:
    with pytest.raises(calendar.EtfCalendarAuthorityError, match="database append failed"):
        signed_envelope(appender=MemoryAppender(fail=True))


def test_postgres_appender_verifies_then_emits_one_insert() -> None:
    envelope = signed_envelope()

    class FakeConnection:
        dialect = SimpleNamespace(name="postgresql")

        def __init__(self) -> None:
            self.statements = []

        def execute(self, statement) -> None:
            self.statements.append(statement)

    connection = FakeConnection()
    appender = PostgresTrustedAcquisitionAppender(connection, registry=TEST_REGISTRY)
    assert appender.append(envelope) == envelope["envelope_sha256"]
    assert len(connection.statements) == 1
    sql = str(connection.statements[0].compile(dialect=__import__(
        "sqlalchemy.dialects.postgresql", fromlist=["dialect"]
    ).dialect()))
    assert "INSERT INTO research.etf_calendar_trusted_acquisitions" in sql
    assert "ON CONFLICT (envelope_sha256) DO NOTHING" in sql
    assert "UPDATE" not in sql and "DELETE" not in sql


def test_postgresql_schema_and_privileges_are_frozen() -> None:
    sql = render_upgrade_sql("postgresql+psycopg://example.invalid/btc_predictor")
    assert "CREATE TABLE research.etf_calendar_trusted_acquisitions" in sql
    assert "PRIMARY KEY (envelope_sha256)" in sql
    assert "signature_algorithm = 'Ed25519'" in sql
    assert "REVOKE ALL ON TABLE research.etf_calendar_trusted_acquisitions FROM PUBLIC" in sql
    assert "GRANT USAGE ON SCHEMA research TO btc_calendar_collector_writer" in sql
    assert "GRANT SELECT, INSERT ON TABLE research.etf_calendar_trusted_acquisitions TO btc_calendar_collector_writer" in sql
    assert "REVOKE UPDATE, DELETE ON TABLE research.etf_calendar_trusted_acquisitions FROM btc_calendar_collector_writer" in sql
    assert "GRANT SELECT ON TABLE research.etf_calendar_trusted_acquisitions TO btc_predictor_scientific_reader" in sql
    assert "GRANT USAGE ON SCHEMA research TO btc_predictor_scientific_reader" in sql
    assert "REVOKE INSERT, UPDATE, DELETE ON TABLE research.etf_calendar_trusted_acquisitions FROM btc_predictor_scientific_reader" in sql


def test_authority_artifacts_reproduce_and_bind_every_material_child(tmp_path: Path) -> None:
    protocol = authority.authority_definition()
    assert protocol["final_classification"] == authority.FINAL_CLASSIFICATION
    assert protocol["material_child_count"] == len(authority._CHILD_ARTIFACTS) == 8
    generated = authority.write_artifacts(tmp_path)
    assert generated == protocol
    assert authority.restore_artifacts(tmp_path) == protocol
    persisted = authority.restore_artifacts(ROOT / authority.OUTPUT_NAMESPACE)
    assert persisted == protocol


def test_every_authority_material_child_mutation_moves_top_hash(monkeypatch) -> None:
    baseline = authority.authority_definition()["definition_sha256"]
    for _, builder_name in authority._CHILD_ARTIFACTS:
        original = getattr(authority, builder_name)

        def mutated(original=original):
            payload = original()
            payload.pop("definition_sha256")
            payload["hostile_mutation"] = True
            return authority._definition(payload)

        with monkeypatch.context() as context:
            context.setattr(authority, builder_name, mutated)
            assert authority.authority_definition()["definition_sha256"] != baseline


def test_repository_contains_no_pem_private_key_material() -> None:
    pem_private_marker = b"BEGIN " + b"PRIVATE KEY"
    tracked = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    for relative in tracked:
        path = ROOT / relative
        if path.is_file() and path.stat().st_size <= 2_000_000:
            assert pem_private_marker not in path.read_bytes(), relative
