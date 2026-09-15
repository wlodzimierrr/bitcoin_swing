"""Cryptographic origin boundary for persisted scientific acquisitions.

Only the trusted collector receives an :class:`AcquisitionSigner`.  Replay
processes receive the frozen public registry and verify immutable envelopes;
they never need, load, or expose the signing private key.
"""

from __future__ import annotations

import ast
import base64
import hashlib
import inspect
import json
import os
import stat
import textwrap
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    load_pem_private_key,
)


AUTHORITY_VERSION = "TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1"
ENVELOPE_KIND = "TRUSTED_ACQUISITION_ENVELOPE_V1"
DOMAIN_SEPARATOR = "BTC_PREDICTOR_TRUSTED_ACQUISITION_ENVELOPE_V1"
SIGNATURE_ALGORITHM = "Ed25519"
PRODUCTION_KEY_ID = "BTC_ETF_CALENDAR_COLLECTOR_ED25519_V1"
PRODUCTION_PUBLIC_KEY_BASE64 = "w71Gv0UzPRK1gmZH0p9wWYqRh6uColYpk3kK2FPUv88="
PRODUCTION_PUBLIC_KEY_SHA256 = "8540303bf79b540bac83ef4dbf7315007c8ab7840fe017ee0b748177063443b9"
PRIVATE_KEY_FILE_ENV_VAR = "BTC_TRUSTED_ACQUISITION_PRIVATE_KEY_FILE"
CRYPTOGRAPHY_VERSION = "50.0.1"


class TrustedAcquisitionError(ValueError):
    """Raised when trusted acquisition creation or replay must refuse."""


@dataclass(frozen=True)
class VerificationKey:
    key_id: str
    algorithm: str
    public_key_base64: str
    public_key_sha256: str
    authority_version: str
    status: str


_PRODUCTION_VERIFICATION_KEY = VerificationKey(
        key_id=PRODUCTION_KEY_ID,
        algorithm=SIGNATURE_ALGORITHM,
        public_key_base64=PRODUCTION_PUBLIC_KEY_BASE64,
        public_key_sha256=PRODUCTION_PUBLIC_KEY_SHA256,
        authority_version=AUTHORITY_VERSION,
        status="ACTIVE",
    )
PRODUCTION_KEY_REGISTRY: Mapping[str, VerificationKey] = MappingProxyType(
    {PRODUCTION_KEY_ID: _PRODUCTION_VERIFICATION_KEY}
)


def canonical_json_bytes(payload: Any) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as error:
        raise TrustedAcquisitionError("payload is not canonical-JSON serializable") from error


def sha256_json(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def canonical_signed_message(
    *, signed_payload_sha256: str, signing_key_id: str
) -> bytes:
    """Build the unambiguous domain-separated message signed by the collector."""

    if not _is_sha256(signed_payload_sha256):
        raise TrustedAcquisitionError("signed payload SHA-256 is invalid")
    if not isinstance(signing_key_id, str) or not signing_key_id:
        raise TrustedAcquisitionError("signing key ID is invalid")
    return canonical_json_bytes(
        {
            "authority_identity": AUTHORITY_VERSION,
            "domain_separator": DOMAIN_SEPARATOR,
            "schema_identity": ENVELOPE_KIND,
            "signed_payload_sha256": signed_payload_sha256,
            "signing_key_id": signing_key_id,
        }
    )


def _decode_public_key(entry: VerificationKey) -> Ed25519PublicKey:
    if (
        entry.algorithm != SIGNATURE_ALGORITHM
        or entry.authority_version != AUTHORITY_VERSION
        or entry.status != "ACTIVE"
    ):
        raise TrustedAcquisitionError("verification key is not active for this authority")
    try:
        raw = base64.b64decode(entry.public_key_base64, validate=True)
    except Exception as error:
        raise TrustedAcquisitionError("verification public key encoding is invalid") from error
    if base64.b64encode(raw).decode("ascii") != entry.public_key_base64:
        raise TrustedAcquisitionError("verification public key encoding is noncanonical")
    if len(raw) != 32 or hashlib.sha256(raw).hexdigest() != entry.public_key_sha256:
        raise TrustedAcquisitionError("verification public-key fingerprint mismatch")
    try:
        return Ed25519PublicKey.from_public_bytes(raw)
    except ValueError as error:
        raise TrustedAcquisitionError("verification public key is invalid") from error


class AcquisitionSigner:
    """Collector-only signing capability; private key bytes are never returned."""

    __slots__ = ("_key", "key_id")

    def __init__(self, key: Ed25519PrivateKey, key_id: str) -> None:
        if not isinstance(key, Ed25519PrivateKey):
            raise TrustedAcquisitionError("an Ed25519 private key is required")
        if not isinstance(key_id, str) or not key_id:
            raise TrustedAcquisitionError("signing key ID is invalid")
        self._key = key
        self.key_id = key_id

    @classmethod
    def from_external_secret(
        cls,
        *, environ: Mapping[str, str] | None = None,
    ) -> AcquisitionSigner:
        """Load the production key from one POSIX owner-protected file descriptor."""

        _assert_runtime_semantics()
        if not hasattr(os, "geteuid") or not hasattr(os, "O_NOFOLLOW"):
            raise TrustedAcquisitionError(
                "production private-key loading requires POSIX ownership and O_NOFOLLOW"
            )

        source = os.environ if environ is None else environ
        configured = source.get(PRIVATE_KEY_FILE_ENV_VAR)
        if not configured:
            raise TrustedAcquisitionError("production collector private key is unavailable")
        flags = os.O_RDONLY | os.O_NOFOLLOW
        try:
            descriptor = os.open(configured, flags)
        except OSError as error:
            raise TrustedAcquisitionError("production collector private key is unavailable") from error
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise TrustedAcquisitionError("collector private-key path is not a regular file")
            if metadata.st_uid != os.geteuid():
                raise TrustedAcquisitionError("collector private-key file owner is not the effective user")
            if metadata.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
                raise TrustedAcquisitionError("collector private-key file permissions are not owner-only")
            with os.fdopen(descriptor, "rb", closefd=True) as stream:
                descriptor = -1
                key_bytes = stream.read()
        except OSError as error:
            raise TrustedAcquisitionError("collector private key could not be read") from error
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        try:
            loaded = load_pem_private_key(key_bytes, password=None)
        except (TypeError, ValueError) as error:
            raise TrustedAcquisitionError("collector private key could not be loaded") from error
        signer = cls(loaded, PRODUCTION_KEY_ID)
        signer._assert_registry_match(PRODUCTION_KEY_REGISTRY)
        return signer

    @classmethod
    def generate_test_only(cls, key_id: str = "TEST_ONLY_ED25519_V1") -> AcquisitionSigner:
        if not key_id.startswith("TEST_ONLY_"):
            raise TrustedAcquisitionError("generated keys must use a test-only key ID")
        return cls(Ed25519PrivateKey.generate(), key_id)

    def verification_key(self, *, authority_version: str = AUTHORITY_VERSION) -> VerificationKey:
        raw = self._key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        return VerificationKey(
            key_id=self.key_id,
            algorithm=SIGNATURE_ALGORITHM,
            public_key_base64=base64.b64encode(raw).decode("ascii"),
            public_key_sha256=hashlib.sha256(raw).hexdigest(),
            authority_version=authority_version,
            status="ACTIVE",
        )

    def _assert_registry_match(self, registry: Mapping[str, VerificationKey]) -> None:
        expected = registry.get(self.key_id)
        if expected is None or expected != self.verification_key():
            raise TrustedAcquisitionError("private key does not match the frozen registry")

    def sign_payload(self, signed_payload: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(signed_payload)
        digest = sha256_json(payload)
        signature = self._key.sign(
            canonical_signed_message(
                signed_payload_sha256=digest,
                signing_key_id=self.key_id,
            )
        )
        envelope = {
            "record_kind": ENVELOPE_KIND,
            "schema_version": 1,
            "authority_identity": AUTHORITY_VERSION,
            "signed_payload": payload,
            "signed_payload_sha256": digest,
            "signing_key_id": self.key_id,
            "signature_algorithm": SIGNATURE_ALGORITHM,
            "signature": base64.b64encode(signature).decode("ascii"),
        }
        envelope["envelope_sha256"] = sha256_json(envelope)
        return envelope


class AcquisitionAppender(Protocol):
    """Collector-only durable append capability."""

    def append(self, envelope: Mapping[str, Any]) -> str: ...


def _verify_envelope_against_key_non_authoritative_test_only(
    envelope: Mapping[str, Any],
    *,
    verification_key: VerificationKey,
) -> dict[str, Any]:
    """Generic cryptographic plumbing; never a production authority boundary."""

    row = dict(envelope)
    required = {
        "record_kind",
        "schema_version",
        "authority_identity",
        "signed_payload",
        "signed_payload_sha256",
        "signing_key_id",
        "signature_algorithm",
        "signature",
        "envelope_sha256",
    }
    if set(row) != required or row.get("record_kind") != ENVELOPE_KIND:
        raise TrustedAcquisitionError("invalid trusted-acquisition envelope schema")
    if type(row.get("schema_version")) is not int or row.get("schema_version") != 1:
        raise TrustedAcquisitionError("trusted-acquisition schema version must be integer 1")
    if row.get("authority_identity") != AUTHORITY_VERSION:
        raise TrustedAcquisitionError("wrong trusted-acquisition authority identity")
    declared_envelope_sha = row.pop("envelope_sha256", None)
    if not _is_sha256(declared_envelope_sha) or sha256_json(row) != declared_envelope_sha:
        raise TrustedAcquisitionError("envelope SHA-256 does not recompute")
    payload = row.get("signed_payload")
    if not isinstance(payload, Mapping):
        raise TrustedAcquisitionError("signed acquisition payload must be an object")
    payload_digest = row.get("signed_payload_sha256")
    if not _is_sha256(payload_digest) or sha256_json(dict(payload)) != payload_digest:
        raise TrustedAcquisitionError("signed payload SHA-256 does not recompute")
    key_id = row.get("signing_key_id")
    entry = verification_key
    if not isinstance(key_id, str) or entry.key_id != key_id:
        raise TrustedAcquisitionError("signing key ID is not frozen by this registry")
    if row.get("signature_algorithm") != SIGNATURE_ALGORITHM:
        raise TrustedAcquisitionError("signature algorithm must be Ed25519")
    try:
        encoded_signature = row.get("signature")
        if not isinstance(encoded_signature, str):
            raise ValueError
        signature = base64.b64decode(encoded_signature, validate=True)
    except Exception as error:
        raise TrustedAcquisitionError("signature encoding is invalid") from error
    if len(signature) != 64:
        raise TrustedAcquisitionError("Ed25519 signature length is invalid")
    if base64.b64encode(signature).decode("ascii") != encoded_signature:
        raise TrustedAcquisitionError("signature encoding is noncanonical")
    try:
        _decode_public_key(entry).verify(
            signature,
            canonical_signed_message(
                signed_payload_sha256=payload_digest,
                signing_key_id=key_id,
            ),
        )
    except InvalidSignature as error:
        raise TrustedAcquisitionError("trusted-acquisition signature is invalid") from error
    return dict(payload)


def verify_production_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Verify authoritative evidence against the one frozen production key."""

    _assert_runtime_semantics()
    return _verify_envelope_against_key_non_authoritative_test_only(
        envelope, verification_key=_PRODUCTION_VERIFICATION_KEY
    )


def verify_test_envelope_non_authoritative_test_only(
    envelope: Mapping[str, Any], verification_key: VerificationKey
) -> dict[str, Any]:
    """Verify test material without making it admissible to production owners."""

    if not verification_key.key_id.startswith("TEST_ONLY_"):
        raise TrustedAcquisitionError("test verifier requires a test-only key")
    return _verify_envelope_against_key_non_authoritative_test_only(
        envelope, verification_key=verification_key
    )


def executable_semantic_sha256() -> str:
    owners = (
        canonical_json_bytes,
        sha256_json,
        canonical_signed_message,
        _decode_public_key,
        _verify_envelope_against_key_non_authoritative_test_only,
        verify_production_envelope,
        AcquisitionSigner.sign_payload,
        AcquisitionSigner.from_external_secret,
        _assert_runtime_semantics,
    )
    normalized = [
        ast.dump(
            ast.parse(textwrap.dedent(inspect.getsource(owner))),
            annotate_fields=True,
            include_attributes=False,
        )
        for owner in owners
    ]
    return sha256_json(normalized)


def _assert_runtime_semantics() -> None:
    """Refuse authoritative work when runtime code differs from the frozen artifact."""

    from btc_predictor.research.trusted_acquisition_authority import (
        assert_frozen_runtime_semantics,
    )

    assert_frozen_runtime_semantics()
