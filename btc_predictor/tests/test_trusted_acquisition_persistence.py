"""POSTP1-001V2B hostile cryptographic and persistence regressions."""

from __future__ import annotations

import base64
import copy
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import inspect
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)

from btc_predictor.db import render_upgrade_sql
from btc_predictor.research import etf_publication_calendar as calendar
from btc_predictor.research import trusted_acquisition as trusted
from btc_predictor.research import trusted_acquisition_authority as authority
from btc_predictor.research import trusted_acquisition_persistence as persistence
from btc_predictor.research.trusted_acquisition_persistence import (
    PostgresTrustedAcquisitionAppender,
    append_production_envelope_committed,
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
        trusted.verify_test_envelope_non_authoritative_test_only(
            envelope, TEST_SIGNER.verification_key()
        )
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
        return calendar._collect_official_calendar_non_authoritative_test_only(
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


def non_authoritative_test_store(envelope: dict) -> calendar.CalendarEvidenceStore:
    payload = trusted.verify_test_envelope_non_authoritative_test_only(
        envelope, TEST_SIGNER.verification_key()
    )
    source = calendar._verify_source_snapshot(payload)
    store = calendar.CalendarEvidenceStore()
    store._envelopes[envelope["envelope_sha256"]] = copy.deepcopy(envelope)
    store._records[source[calendar.RECORD_DIGEST_FIELD]] = source
    return store


def test_production_registry_is_one_frozen_ed25519_public_key() -> None:
    assert list(trusted.PRODUCTION_KEY_REGISTRY) == [trusted.PRODUCTION_KEY_ID]
    entry = trusted.PRODUCTION_KEY_REGISTRY[trusted.PRODUCTION_KEY_ID]
    public = base64.b64decode(entry.public_key_base64, validate=True)
    assert entry.algorithm == "Ed25519"
    assert entry.status == "ACTIVE"
    assert hashlib.sha256(public).hexdigest() == entry.public_key_sha256
    assert TEST_SIGNER.key_id not in trusted.PRODUCTION_KEY_REGISTRY
    assert TEST_SIGNER.verification_key().public_key_base64 != entry.public_key_base64
    with pytest.raises(TypeError):
        trusted.PRODUCTION_KEY_REGISTRY[TEST_SIGNER.key_id] = TEST_SIGNER.verification_key()
    assert not hasattr(trusted.PRODUCTION_KEY_REGISTRY, "update")
    with pytest.raises(trusted.TrustedAcquisitionError, match="not frozen"):
        trusted.verify_production_envelope(signed_envelope())


def test_missing_production_private_key_has_no_default_or_fallback() -> None:
    with pytest.raises(trusted.TrustedAcquisitionError, match="unavailable"):
        trusted.AcquisitionSigner.from_external_secret(environ={})


def test_private_key_loader_uses_same_owner_protected_descriptor(tmp_path: Path) -> None:
    key_path = tmp_path / "collector.pem"
    key_path.write_bytes(
        Ed25519PrivateKey.generate().private_bytes(
            Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
        )
    )
    key_path.chmod(0o600)
    with pytest.raises(trusted.TrustedAcquisitionError, match="does not match"):
        trusted.AcquisitionSigner.from_external_secret(
            environ={trusted.PRIVATE_KEY_FILE_ENV_VAR: str(key_path)}
        )
    key_path.chmod(0o640)
    with pytest.raises(trusted.TrustedAcquisitionError, match="owner-only"):
        trusted.AcquisitionSigner.from_external_secret(
            environ={trusted.PRIVATE_KEY_FILE_ENV_VAR: str(key_path)}
        )
    symlink = tmp_path / "collector-link.pem"
    symlink.symlink_to(key_path)
    with pytest.raises(trusted.TrustedAcquisitionError, match="unavailable"):
        trusted.AcquisitionSigner.from_external_secret(
            environ={trusted.PRIVATE_KEY_FILE_ENV_VAR: str(symlink)}
        )


def test_private_key_loader_refuses_wrong_effective_owner(tmp_path: Path) -> None:
    key_path = tmp_path / "collector.pem"
    key_path.write_bytes(b"not reached")
    key_path.chmod(0o600)
    real_fstat = os.fstat

    def wrong_owner(descriptor: int):
        metadata = real_fstat(descriptor)
        return SimpleNamespace(st_mode=metadata.st_mode, st_uid=os.geteuid() + 1)

    with (
        patch.object(os, "fstat", side_effect=wrong_owner),
        pytest.raises(trusted.TrustedAcquisitionError, match="effective user"),
    ):
        trusted.AcquisitionSigner.from_external_secret(
            environ={trusted.PRIVATE_KEY_FILE_ENV_VAR: str(key_path)}
        )


def test_deterministic_ed25519_compatibility_vector() -> None:
    first = TEST_SIGNER.sign_payload({"vector": "POSTP1-001V2B", "n": 1})
    second = TEST_SIGNER.sign_payload({"n": 1, "vector": "POSTP1-001V2B"})
    assert first == second
    assert first["signature"] == (
        "VmFs58MvkGMOlgBeJqS3PPEKE4pjVqxid4hmL1MrWJM8fYVIlnCvnATJ11GQK76ZlAv2B/"
        "n9F14ZAE7gkCh9BQ=="
    )
    assert trusted.verify_test_envelope_non_authoritative_test_only(
        first, TEST_SIGNER.verification_key()
    ) == {
        "n": 1,
        "vector": "POSTP1-001V2B",
    }


@pytest.mark.parametrize("schema_version", [True, False, 1.0, "1"])
def test_schema_version_is_type_strict(schema_version) -> None:
    envelope = TEST_SIGNER.sign_payload({"strict": True})
    envelope["schema_version"] = schema_version
    envelope["envelope_sha256"] = trusted.sha256_json(
        {key: value for key, value in envelope.items() if key != "envelope_sha256"}
    )
    with pytest.raises(trusted.TrustedAcquisitionError, match="schema version"):
        trusted.verify_test_envelope_non_authoritative_test_only(
            envelope, TEST_SIGNER.verification_key()
        )


def test_noncanonical_signature_base64_is_refused() -> None:
    envelope = TEST_SIGNER.sign_payload({"strict": True})
    canonical = envelope["signature"]
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    index = alphabet.index(canonical[-3])
    envelope["signature"] = canonical[:-3] + alphabet[index ^ 1] + "=="
    envelope["envelope_sha256"] = trusted.sha256_json(
        {key: value for key, value in envelope.items() if key != "envelope_sha256"}
    )
    assert base64.b64decode(envelope["signature"]) == base64.b64decode(canonical)
    with pytest.raises(trusted.TrustedAcquisitionError, match="noncanonical"):
        trusted.verify_test_envelope_non_authoritative_test_only(
            envelope, TEST_SIGNER.verification_key()
        )


def test_noncanonical_public_key_base64_is_refused() -> None:
    entry = TEST_SIGNER.verification_key()
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    index = alphabet.index(entry.public_key_base64[-2])
    noncanonical = entry.public_key_base64[:-2] + alphabet[index ^ 1] + "="
    assert base64.b64decode(noncanonical) == base64.b64decode(entry.public_key_base64)
    changed = trusted.VerificationKey(
        **{**entry.__dict__, "public_key_base64": noncanonical}
    )
    with pytest.raises(trusted.TrustedAcquisitionError, match="noncanonical"):
        trusted._decode_public_key(changed)


def test_self_hashed_unsigned_forgery_and_copied_trust_fields_refused() -> None:
    forged = signed_envelope()["signed_payload"]
    assert forged["acquisition_provenance"] == calendar.TRUSTED_ACQUISITION_PROVENANCE
    assert forged["collector_semantic_sha256"] == calendar._semantic_ast_sha256()
    with pytest.raises(calendar.EtfCalendarAuthorityError, match="unsigned acquisition refused"):
        calendar.CalendarEvidenceStore().put(forged)


def test_test_key_and_random_signature_are_refused_by_production_registry() -> None:
    envelope = signed_envelope()
    with pytest.raises(trusted.TrustedAcquisitionError, match="not frozen"):
        trusted.verify_production_envelope(envelope)
    random_signature = copy.deepcopy(envelope)
    random_signature["signature"] = base64.b64encode(bytes(64)).decode("ascii")
    random_signature.pop("envelope_sha256")
    random_signature["envelope_sha256"] = trusted.sha256_json(random_signature)
    with pytest.raises(trusted.TrustedAcquisitionError, match="signature is invalid"):
        trusted.verify_test_envelope_non_authoritative_test_only(
            random_signature, TEST_SIGNER.verification_key()
        )


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
    with pytest.raises(trusted.TrustedAcquisitionError, match="signature is invalid"):
        trusted.verify_test_envelope_non_authoritative_test_only(
            forged, TEST_SIGNER.verification_key()
        )


def test_signature_substitution_and_key_id_substitution_refuse() -> None:
    first = signed_envelope()
    second = copy.deepcopy(first)
    second["signed_payload"]["published_at"] = ACQUIRED.isoformat()
    second = recompute_unsigned_hashes(second)
    second["signature"] = first["signature"]
    second.pop("envelope_sha256")
    second["envelope_sha256"] = trusted.sha256_json(second)
    with pytest.raises(trusted.TrustedAcquisitionError, match="signature is invalid"):
        trusted.verify_test_envelope_non_authoritative_test_only(
            second, TEST_SIGNER.verification_key()
        )

    substituted = copy.deepcopy(first)
    substituted["signing_key_id"] = "TEST_ONLY_OTHER_KEY"
    substituted.pop("envelope_sha256")
    substituted["envelope_sha256"] = trusted.sha256_json(substituted)
    with pytest.raises(trusted.TrustedAcquisitionError, match="not frozen"):
        trusted.verify_test_envelope_non_authoritative_test_only(
            substituted, TEST_SIGNER.verification_key()
        )


def test_test_signed_envelope_replays_only_in_non_authoritative_test_store() -> None:
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
    with pytest.raises(trusted.TrustedAcquisitionError, match="not frozen"):
        rehydrate_verified_envelopes(rows)
    store = non_authoritative_test_store(envelope)
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
from btc_predictor.research.trusted_acquisition import VerificationKey, verify_test_envelope_non_authoritative_test_only
row=json.loads(Path(sys.argv[1]).read_text())
key=VerificationKey(**json.loads(sys.argv[2]))
payload=verify_test_envelope_non_authoritative_test_only(row, key)
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


def test_production_persistence_has_no_connection_or_registry_injection() -> None:
    assert tuple(inspect.signature(PostgresTrustedAcquisitionAppender).parameters) == ()
    assert tuple(inspect.signature(rehydrate_verified_envelopes).parameters) == ("rows",)
    assert tuple(inspect.signature(append_production_envelope_committed).parameters) == (
        "envelope",
    )
    with pytest.raises(TypeError):
        PostgresTrustedAcquisitionAppender(SimpleNamespace(), registry=TEST_REGISTRY)
    with pytest.raises(TypeError):
        calendar.collect_official_calendar(
            "NASDAQ_ETF_CALENDAR_OFFICIAL_V1",
            lambda: ACQUIRED,
            signer=TEST_SIGNER,
            appender=MemoryAppender(),
        )


def test_transaction_owner_requires_commit_and_independent_confirmation(monkeypatch) -> None:
    envelope = signed_envelope()
    payload = envelope["signed_payload"]
    row = {
        **persistence._persistence_values(envelope, payload),
        "envelope_sha256": envelope["envelope_sha256"],
    }

    class Result:
        def mappings(self): return self
        def one_or_none(self): return row

    class Connection:
        def __init__(self, *, confirm=False): self.confirm = confirm
        def execute(self, statement): return Result() if self.confirm else None

    class Context:
        def __init__(self, connection, fail=False): self.connection, self.fail = connection, fail
        def __enter__(self): return self.connection
        def __exit__(self, exc_type, exc, traceback):
            if self.fail and exc_type is None:
                raise RuntimeError("commit failed")

    class Engine:
        dialect = SimpleNamespace(name="postgresql")
        def __init__(self, *, fail_commit=False, fail_confirmation=False):
            self.fail_commit, self.fail_confirmation = fail_commit, fail_confirmation
        def begin(self): return Context(Connection(), self.fail_commit)
        def dispose(self): pass
        def connect(self):
            if self.fail_confirmation:
                raise RuntimeError("confirmation unavailable")
            return Context(Connection(confirm=True))

    monkeypatch.setattr(
        persistence, "rehydrate_verified_envelopes", lambda rows: (copy.deepcopy(envelope),)
    )
    identity_connections = []
    monkeypatch.setattr(
        persistence,
        "assert_authorized_collector_database_identity",
        lambda connection: identity_connections.append(connection),
    )
    assert persistence._append_with_owned_engine_non_authoritative_test_only(
        Engine(), envelope=envelope, payload=payload
    ) == envelope["envelope_sha256"]
    assert len(identity_connections) == 2
    for engine in (Engine(fail_commit=True), Engine(fail_confirmation=True)):
        with pytest.raises(trusted.TrustedAcquisitionError, match=persistence.COMMIT_UNCONFIRMED):
            persistence._append_with_owned_engine_non_authoritative_test_only(
                engine, envelope=envelope, payload=payload
            )


def test_database_identity_failure_refuses_before_insert(monkeypatch) -> None:
    envelope = signed_envelope()

    class Connection:
        inserted = False
        def execute(self, statement):
            self.inserted = True

    connection = Connection()

    class Context:
        def __enter__(self): return connection
        def __exit__(self, exc_type, exc, traceback): return False

    class Engine:
        dialect = SimpleNamespace(name="postgresql")
        def begin(self): return Context()
        def dispose(self): pass

    def refuse(connection):
        raise trusted.TrustedAcquisitionError(persistence.DATABASE_IDENTITY_INVALID)

    monkeypatch.setattr(persistence, "assert_authorized_collector_database_identity", refuse)
    with pytest.raises(
        trusted.TrustedAcquisitionError, match=persistence.DATABASE_IDENTITY_INVALID
    ):
        persistence._append_with_owned_engine_non_authoritative_test_only(
            Engine(), envelope=envelope, payload=envelope["signed_payload"]
        )
    assert connection.inserted is False


def test_denormalized_projection_tampering_refuses() -> None:
    payload = signed_envelope()["signed_payload"]
    row = {"response_sha256": "0" * 64}
    with pytest.raises(trusted.TrustedAcquisitionError, match="projection mismatch"):
        persistence._assert_projection_equality(row, payload)


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
    assert "CREATE ROLE btc_calendar_collector_writer NOLOGIN NOSUPERUSER" in sql
    assert "CREATE ROLE btc_predictor_scientific_reader NOLOGIN NOSUPERUSER" in sql
    assert "REVOKE CREATE ON SCHEMA research FROM PUBLIC" in sql
    assert "REVOKE CREATE ON SCHEMA research FROM btc_calendar_collector_writer" in sql
    assert "REVOKE CREATE ON SCHEMA research FROM btc_predictor_scientific_reader" in sql


def test_authority_artifacts_reproduce_and_bind_every_material_child(tmp_path: Path) -> None:
    protocol = authority.authority_definition()
    assert protocol["final_classification"] == authority.FINAL_CLASSIFICATION
    assert protocol["material_child_count"] == len(authority._CHILD_ARTIFACTS) == 9
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


def test_runtime_semantic_mutation_refuses_old_frozen_artifact(monkeypatch) -> None:
    authority.assert_frozen_runtime_semantics()
    monkeypatch.setattr(trusted, "_decode_public_key", lambda entry: Ed25519PrivateKey.generate().public_key())
    with pytest.raises(trusted.TrustedAcquisitionError, match="differs from frozen"):
        authority.assert_frozen_runtime_semantics()


def test_runtime_production_key_replacement_refuses_in_isolated_process() -> None:
    script = """
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from btc_predictor.research import trusted_acquisition as trusted
from btc_predictor.research import trusted_acquisition_authority as authority
replacement_signer = trusted.AcquisitionSigner(
    Ed25519PrivateKey.generate(), trusted.PRODUCTION_KEY_ID
)
trusted._PRODUCTION_VERIFICATION_KEY = replacement_signer.verification_key()
try:
    trusted.verify_production_envelope(replacement_signer.sign_payload({'forged': True}))
except trusted.TrustedAcquisitionError as error:
    print(str(error))
else:
    raise SystemExit('replacement key remained authoritative')
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT.parent,
        env=dict(os.environ, PYTHONPATH=str(ROOT)),
        check=True,
        capture_output=True,
        text=True,
    )
    assert "material values differ" in completed.stdout


@pytest.mark.parametrize(
    ("target", "replacement"),
    [
        ("AUTHORITY_VERSION", "TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V999"),
        ("ENVELOPE_KIND", "TRUSTED_ACQUISITION_ENVELOPE_V999"),
        ("DOMAIN_SEPARATOR", "FORGED_DOMAIN_SEPARATOR"),
        ("SIGNATURE_ALGORITHM", "FORGED_ED25519"),
        ("PRODUCTION_KEY_ID", "FORGED_PRODUCTION_KEY"),
    ],
)
def test_runtime_authority_material_scalar_replacement_refuses(
    monkeypatch, target: str, replacement: str
) -> None:
    monkeypatch.setattr(trusted, target, replacement)
    with pytest.raises(trusted.TrustedAcquisitionError, match="material values differ"):
        authority.assert_frozen_production_material_values()


@pytest.mark.parametrize(
    "field",
    [
        "key_id",
        "algorithm",
        "public_key_base64",
        "public_key_sha256",
        "authority_version",
        "status",
    ],
)
def test_effective_production_verification_key_material_replacement_refuses(
    monkeypatch, field: str
) -> None:
    values = trusted._PRODUCTION_VERIFICATION_KEY.__dict__.copy()
    values[field] = f"FORGED_{values[field]}"
    monkeypatch.setattr(trusted, "_PRODUCTION_VERIFICATION_KEY", trusted.VerificationKey(**values))
    with pytest.raises(trusted.TrustedAcquisitionError, match="material values differ"):
        authority.assert_frozen_production_material_values()


def test_runtime_registry_content_replacement_refuses(monkeypatch) -> None:
    replacement = trusted.AcquisitionSigner(
        Ed25519PrivateKey.generate(), trusted.PRODUCTION_KEY_ID
    ).verification_key()
    monkeypatch.setattr(trusted, "PRODUCTION_KEY_REGISTRY", {trusted.PRODUCTION_KEY_ID: replacement})
    with pytest.raises(trusted.TrustedAcquisitionError, match="material values differ"):
        authority.assert_frozen_production_material_values()


def test_runtime_registry_mapping_key_replacement_refuses(monkeypatch) -> None:
    monkeypatch.setattr(
        trusted,
        "PRODUCTION_KEY_REGISTRY",
        {"FORGED_REGISTRY_KEY": trusted._PRODUCTION_VERIFICATION_KEY},
    )
    with pytest.raises(trusted.TrustedAcquisitionError, match="material values differ"):
        authority.assert_frozen_production_material_values()


def test_material_attestation_refuses_missing_or_unbound_persisted_child(
    monkeypatch, tmp_path: Path
) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setattr(authority, "OUTPUT_NAMESPACE", str(missing))
    with pytest.raises(trusted.TrustedAcquisitionError, match="unavailable"):
        authority.assert_frozen_production_material_values()

    copied = tmp_path / "copied"
    shutil.copytree(ROOT / "prospective_evidence/trusted_acquisition_persistence_authority_v1_r2", copied)
    child_path = copied / "signing_key_registry.json"
    child = json.loads(child_path.read_text(encoding="ascii"))
    child["keys"][0]["status"] = "FORGED"
    child_path.write_text(json.dumps(child), encoding="ascii")
    monkeypatch.setattr(authority, "OUTPUT_NAMESPACE", str(copied))
    with pytest.raises(trusted.TrustedAcquisitionError, match="digest is invalid"):
        authority.assert_frozen_production_material_values()

    child.pop("definition_sha256", None)
    child["definition_sha256"] = trusted.sha256_json(child)
    child_path.write_text(json.dumps(child), encoding="ascii")
    parent_path = copied / authority.PROTOCOL_FILENAME
    parent = json.loads(parent_path.read_text(encoding="ascii"))
    parent["child_definition_sha256"]["signing_key_registry"] = child["definition_sha256"]
    parent.pop("definition_sha256", None)
    parent["definition_sha256"] = trusted.sha256_json(parent)
    parent_path.write_text(json.dumps(parent), encoding="ascii")
    with pytest.raises(trusted.TrustedAcquisitionError, match="frozen expected identity"):
        authority.assert_frozen_production_material_values()


def test_authority_hash_and_artifacts_are_process_cwd_and_hashseed_deterministic(
    tmp_path: Path,
) -> None:
    hashes = []
    for seed, cwd in (("1", ROOT), ("8675309", tmp_path)):
        output = tmp_path / f"generated-{seed}"
        script = """
import sys
from pathlib import Path
from btc_predictor.research import trusted_acquisition_authority as authority
print(authority.write_artifacts(Path(sys.argv[1]))['definition_sha256'])
"""
        completed = subprocess.run(
            [sys.executable, "-c", script, str(output)],
            cwd=cwd,
            env=dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=str(ROOT)),
            check=True,
            capture_output=True,
            text=True,
        )
        hashes.append(completed.stdout.strip())
    assert hashes == [authority.FROZEN_AUTHORITY_DEFINITION_SHA256] * 2
    first = tmp_path / "generated-1"
    second = tmp_path / "generated-8675309"
    assert {
        path.name: path.read_bytes() for path in first.iterdir()
    } == {
        path.name: path.read_bytes() for path in second.iterdir()
    }


def test_authority_hash_is_independent_of_material_child_input_order(
    monkeypatch, tmp_path: Path
) -> None:
    baseline = authority.authority_definition()
    monkeypatch.setattr(authority, "_CHILD_ARTIFACTS", tuple(reversed(authority._CHILD_ARTIFACTS)))
    assert authority.authority_definition() == baseline
    generated = authority.write_artifacts(tmp_path)
    assert generated["definition_sha256"] == authority.FROZEN_AUTHORITY_DEFINITION_SHA256


def _valid_database_identity() -> dict:
    return {
        "session_user": "collector_login",
        "current_user": "collector_login",
        "database_name": "disposable",
        "session_or_current_is_collector_member": True,
        "collector_role_exists": True,
        "collector_role_nologin": True,
        "collector_role_safe": True,
        "collector_role_has_no_membership": True,
        "session_user_superuser": False,
        "current_user_superuser": False,
        "session_user_database_owner": False,
        "current_user_database_owner": False,
        "session_user_schema_owner": False,
        "current_user_schema_owner": False,
        "session_user_table_owner": False,
        "current_user_table_owner": False,
        "table_select": True,
        "table_insert": True,
        "table_update": False,
        "table_delete": False,
        "schema_usage": True,
        "schema_create": False,
    }


@pytest.mark.parametrize(
    ("field", "unsafe"),
    [
        ("session_or_current_is_collector_member", False),
        ("collector_role_nologin", False),
        ("collector_role_safe", False),
        ("collector_role_has_no_membership", False),
        ("session_user_superuser", True),
        ("current_user_superuser", True),
        ("session_user_database_owner", True),
        ("current_user_database_owner", True),
        ("session_user_schema_owner", True),
        ("current_user_schema_owner", True),
        ("session_user_table_owner", True),
        ("current_user_table_owner", True),
        ("table_select", False),
        ("table_insert", False),
        ("table_update", True),
        ("table_delete", True),
        ("schema_usage", False),
        ("schema_create", True),
    ],
)
def test_database_identity_and_privilege_mismatch_refuses(
    monkeypatch, field: str, unsafe: bool
) -> None:
    snapshot = _valid_database_identity()
    snapshot[field] = unsafe
    monkeypatch.setattr(persistence, "_database_identity_snapshot", lambda connection: snapshot)
    with pytest.raises(
        trusted.TrustedAcquisitionError, match=persistence.DATABASE_IDENTITY_INVALID
    ):
        persistence.assert_authorized_collector_database_identity(SimpleNamespace())


def test_database_identity_pass_returns_session_and_current_user(monkeypatch) -> None:
    snapshot = _valid_database_identity()
    monkeypatch.setattr(persistence, "_database_identity_snapshot", lambda connection: snapshot)
    assert persistence.assert_authorized_collector_database_identity(SimpleNamespace()) == snapshot


def test_database_identity_snapshot_queries_actual_postgresql_session() -> None:
    snapshot = _valid_database_identity()

    class Result:
        def mappings(self): return self
        def one(self): return snapshot

    class Connection:
        def execute(self, statement, parameters):
            sql = str(statement)
            for required in (
                "session_user::text",
                "current_user::text",
                "pg_has_role",
                "pg_catalog.pg_roles",
                "pg_catalog.pg_database",
                "pg_catalog.pg_namespace",
                "pg_catalog.pg_class",
                "has_table_privilege",
                "has_schema_privilege",
            ):
                assert required in sql
            assert parameters == {
                "collector_role": persistence.COLLECTOR_ROLE,
                "schema_name": persistence.AUTHORITATIVE_SCHEMA,
                "table_name": persistence.AUTHORITATIVE_TABLE,
                "table_short_name": "etf_calendar_trusted_acquisitions",
            }
            return Result()

    assert persistence._database_identity_snapshot(Connection()) == snapshot


def test_production_surfaces_have_no_capability_or_trust_root_parameters() -> None:
    production = (
        trusted.verify_production_envelope,
        calendar.CalendarEvidenceStore,
        PostgresTrustedAcquisitionAppender,
        rehydrate_verified_envelopes,
        calendar.collect_official_calendar,
        append_production_envelope_committed,
    )
    forbidden = {"registry", "key_registry", "verification_keys", "signer", "appender"}
    for owner in production:
        assert forbidden.isdisjoint(inspect.signature(owner).parameters)
    with pytest.raises(TypeError, match="cannot be subclassed"):
        class ForgedStore(calendar.CalendarEvidenceStore):
            pass


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
