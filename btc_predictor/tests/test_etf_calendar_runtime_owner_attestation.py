"""POSTP1-001V2A-PAD3 runtime owner-attestation proof-architecture tests."""

from __future__ import annotations

import copy
import decimal
import functools
import json
import os
import subprocess
import sys
import threading
import types
from pathlib import Path

import pytest

from btc_predictor.research import etf_calendar_compiled_binding_witness as pad2
from btc_predictor.research import etf_calendar_runtime_owner_attestation as attestation
from btc_predictor.research import etf_calendar_store_capability_normal_form_r1 as narrow
from btc_predictor.research import etf_publication_calendar as production


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / attestation.OUTPUT_NAMESPACE
FROZEN_PYTHON = ROOT / ".venv312/bin/python"
CALENDAR_SOURCE_TEXT = attestation.CALENDAR_SOURCE.read_text(encoding="utf-8")
OWNER = ("owner",)


def _production_expectations() -> tuple[attestation.OwnerIdentityExpectation, ...]:
    return attestation.expected_owner_identities(CALENDAR_SOURCE_TEXT)


@pytest.fixture()
def replica(request: pytest.FixtureRequest) -> types.ModuleType:
    """One isolated executable replica of the exact certified calendar source.

    Adversarial runtime mutations are applied here, never to the imported
    production module, so no probe can leak into another test.
    """

    name = f"etf_calendar_replica_{abs(hash(request.node.nodeid)) % 10_000_000}"
    code = compile(
        CALENDAR_SOURCE_TEXT,
        str(attestation.CALENDAR_SOURCE),
        "exec",
        dont_inherit=True,
        optimize=0,
    )
    module = types.ModuleType(name)
    module.__file__ = str(attestation.CALENDAR_SOURCE)
    # The frozen architecture refuses two loaded instances of the certified
    # source, so the real production module is unloaded for the duration of the
    # probe and restored afterwards; the object itself stays alive here.
    canonical = sys.modules.pop(attestation.CALENDAR_MODULE_IMPORT_NAME, None)
    sys.modules[name] = module
    try:
        exec(code, module.__dict__)  # noqa: S102 - isolated attestation replica
        yield module
    finally:
        sys.modules.pop(name, None)
        if canonical is not None:
            sys.modules[attestation.CALENDAR_MODULE_IMPORT_NAME] = canonical


def _replica_expectations(
    module: types.ModuleType,
) -> tuple[attestation.OwnerIdentityExpectation, ...]:
    return attestation.expected_owner_identities(
        CALENDAR_SOURCE_TEXT, module_name=module.__name__
    )


def _epoch(
    module: types.ModuleType,
    expectations: tuple[attestation.OwnerIdentityExpectation, ...],
    epoch_id: str = "epoch-0001",
    closure: attestation.ExecutionClosureExpectation | None = None,
) -> attestation.ScientificExecutionEpoch:
    return attestation.ScientificExecutionEpoch(
        epoch_id=epoch_id,
        module=module,
        expectations=expectations,
        source=CALENDAR_SOURCE_TEXT,
        calendar_authority_sha256=(
            "901f572e03781030906cd6fe72a73ec5804f9ffbdefe6a8a944c067f7fd9853f"
        ),
        proof_architecture_sha256=attestation.runtime_owner_attestation_v1_definition()[
            "definition_sha256"
        ],
        decision_time="2026-09-19T00:00:00Z",
        closure_expectation=closure,
    )


def _closure_expectations(
    module: types.ModuleType,
) -> attestation.ExecutionClosureExpectation:
    return attestation.expected_execution_closure(
        CALENDAR_SOURCE_TEXT, module_name=module.__name__
    )


def _attest(
    module: types.ModuleType,
    expectations: tuple[attestation.OwnerIdentityExpectation, ...],
    closure: attestation.ExecutionClosureExpectation | None = None,
) -> attestation.RuntimeOwnerAttestation:
    return attestation.attest_runtime_owners(
        module,
        expectations,
        attestation.source_sha256(CALENDAR_SOURCE_TEXT),
        closure,
    )


def _reasons_for(
    module: types.ModuleType,
    expectations: tuple[attestation.OwnerIdentityExpectation, ...],
    owner: str,
) -> tuple[str, ...]:
    measured = _attest(module, expectations)
    return next(row.reasons for row in measured.owners if row.owner == owner)


def _refuses_epoch(
    module: types.ModuleType,
    expectations: tuple[attestation.OwnerIdentityExpectation, ...],
    match: str,
) -> attestation.RuntimeOwnerAttestationError:
    calls: list[str] = []

    def operation(attested: types.ModuleType) -> str:
        calls.append("operation")
        return "scientific-result"

    def admit(result: str) -> str:
        calls.append("admit")
        return result

    with pytest.raises(attestation.RuntimeOwnerAttestationError, match=match) as excinfo:
        attestation.run_scientific_execution_epoch(
            _epoch(module, expectations), operation, admit
        )
    assert "admit" not in calls
    return excinfo.value


# ---------------------------------------------------------------------------
# Decision parent and authorization
# ---------------------------------------------------------------------------


def test_parent_freezes_runtime_owner_attestation_and_review_only_authorization() -> None:
    decision = attestation.runtime_owner_attestation_v1_definition()
    assert decision["decision_version"] == "ETF_CALENDAR_RUNTIME_OWNER_ATTESTATION_V1"
    assert decision["program_ticket"] == "POSTP1-001V2A-PAD3"
    assert decision["workstream"] == "EPIC X — PROSPECTIVE INTEGRATION EVIDENCE"
    assert decision["status"] == (
        "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW"
    )
    assert decision["final_classification"] == (
        "ETF_CALENDAR_RUNTIME_OWNER_ATTESTATION_V1_READY_FOR_XHIGH_REVIEW"
    )
    assert decision["proof_strategy"] == (
        "COMPILED_ROOT_WITNESS_PLUS_CLOSED_AST_STORE_USE_GRAMMAR_PLUS_"
        "RUNTIME_SCIENTIFIC_EXECUTION_EPOCH_ATTESTATION"
    )
    assert decision["required_review"] == (
        "POSTP1-002V2A-PAD3_INDEPENDENT_EXACT_HASH_XHIGH_PROOF_ARCHITECTURE_REVIEW"
    )
    assert decision["failed_parent_sha256"] == (
        "b5ca36bfa9b96970b667cc44b10c5c5da7eb5ce7c57e5739601640d9b2a8abe9"
    )
    assert decision["failed_parent_certified"] is False
    assert decision["certified_dependency_sha256"] == (
        "02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772"
    )
    assert decision["authorization"] == {
        "independent_proof_architecture_xhigh_review_may_begin": True,
        "calendar_implementation_may_begin": False,
        "postp1_001v2r1_may_begin": False,
        "prospective_collection_may_begin": False,
    }
    assert decision["material_child_count"] == len(attestation._CHILD_ARTIFACTS) == 16
    assert decision["proof_interpreter"] == dict(attestation.PROOF_INTERPRETER_IDENTITY)


def test_central_decisions_answer_every_frozen_architecture_question() -> None:
    central = attestation.runtime_owner_attestation_v1_definition()["central_decisions"]
    assert central["static_reflection_blacklist_is_owner_identity_proof"] is False
    assert central["reflection_blacklist_complete"] is False
    assert (
        central["effective_owner_identity_measured_at_the_runtime_execution_boundary"]
        is True
    )
    assert central["module_or_function_reflection_syntax_statically_enumerated"] is False
    assert central["code_fingerprint_required"] is True
    assert central["code_object_identity_comparison_is_sufficient"] is False
    assert central["same_module_namespace_required"] is True
    assert central["closure_contract_attested"] is True
    assert central["transitive_execution_closure_attested"] is True
    assert central["builtins_namespace_attested"] is True
    assert central["module_route_identity_attested"] is True
    assert central["consumer_held_owner_bindings_attested"] is True
    assert central["lazy_or_deferred_result_admitted"] is False
    assert central["exception_path_sweeps_for_persistent_drift"] is True
    assert central["defaults_attested"] is True
    assert central["kwdefaults_attested"] is True
    assert central["wrapper_state_attested"] is True
    assert central["pre_execution_attestation_required"] is True
    assert central["post_execution_attestation_required"] is True
    assert central["post_attestation_before_result_admission"] is True
    assert central["startup_attestation_required"] is True
    assert central["startup_attestation_replaces_per_epoch_attestation"] is False
    assert central["compiled_root_witness_preserved"] is True
    assert central["closed_ast_store_use_grammar_preserved"] is True
    assert central["root_may_be_a_cell_variable_of_a_conforming_owner"] is False
    assert central["exact_eleven_owner_graph_preserved"] is True
    assert central["direct_body_dependency_checks_preserved"] is True
    assert central["wrapper_installed_guards_permitted"] is False
    assert central["transient_mutate_and_restore_resistance_claimed"] is False
    assert central["process_isolation_escalation_preserved"] is True
    assert central["threat_model_strengthened"] is False
    assert central["calendar_science_changed"] is False
    assert central["calendar_production_code_changed"] is False


# ---------------------------------------------------------------------------
# Frozen interpreter identity
# ---------------------------------------------------------------------------


def test_frozen_proof_interpreter_identity_is_scientific_proof_material() -> None:
    observed = pad2.verify_proof_interpreter_identity()
    assert observed == dict(attestation.PROOF_INTERPRETER_IDENTITY)
    assert observed["version_major"] == 3
    assert observed["version_minor"] == 12
    assert observed["version_micro"] == 14
    assert observed["cache_tag"] == "cpython-312"
    assert observed["magic_number_hex"] == "cb0d0d0a"


def test_another_interpreter_identity_refuses_scientific_authority() -> None:
    drifted = dict(attestation.PROOF_INTERPRETER_IDENTITY) | {"version_micro": 15}
    with pytest.raises(
        pad2.CompiledBindingWitnessError, match="frozen proof interpreter mismatch"
    ):
        pad2.verify_proof_interpreter_identity(drifted)


# ---------------------------------------------------------------------------
# Owner code execution fingerprint
# ---------------------------------------------------------------------------


def test_code_fingerprint_matches_the_independently_compiled_certified_source() -> None:
    expectations = _production_expectations()
    assert len(expectations) == 11
    for expectation in expectations:
        effective = production.__dict__[expectation.owner]
        assert attestation.owner_code_fingerprint(effective.__code__) == (
            expectation.code_fingerprint
        )
        assert effective.__code__ is not None


def test_independently_compiled_code_objects_are_not_the_same_object() -> None:
    """Object identity would refuse honest sources; the fingerprint is the rule."""

    expectations = _production_expectations()
    module_code = pad2.compile_reviewed_source(
        CALENDAR_SOURCE_TEXT, str(attestation.CALENDAR_SOURCE)
    )
    compiled = {
        code.co_qualname: code for code in pad2._all_code_objects(module_code)
    }
    for expectation in expectations:
        effective = production.__dict__[expectation.owner].__code__
        independent = compiled[expectation.owner]
        assert effective is not independent
        assert attestation.owner_code_fingerprint(effective) == (
            attestation.owner_code_fingerprint(independent)
        )


BASE_OWNER_SOURCE = "def owner(store):\n    return store.get('a')\n"


@pytest.mark.parametrize(
    ("replacement", "identical"),
    [
        (BASE_OWNER_SOURCE, True),
        ("def owner(store):\n    return store.get('b')\n", False),
        ("def owner(store):\n    return store.records()\n", False),
        ("def owner(store):\n    x = 1\n    return store.get('a')\n", False),
        ("def owner(store, *, flag=None):\n    return store.get('a')\n", False),
    ],
)
def test_any_executable_difference_moves_the_code_fingerprint(
    replacement: str, identical: bool
) -> None:
    base = compile(BASE_OWNER_SOURCE, "<base>", "exec", dont_inherit=True)
    other = compile(replacement, "<other>", "exec", dont_inherit=True)
    base_owner = next(
        code for code in base.co_consts if isinstance(code, types.CodeType)
    )
    other_owner = next(
        code for code in other.co_consts if isinstance(code, types.CodeType)
    )
    same = attestation.owner_code_fingerprint(base_owner) == (
        attestation.owner_code_fingerprint(other_owner)
    )
    assert same is identical


def test_code_fingerprint_excludes_only_the_source_path() -> None:
    first = compile("def owner(store):\n    return store.get('a')\n", "<a>", "exec")
    second = compile("def owner(store):\n    return store.get('a')\n", "<b>", "exec")
    first_owner = next(c for c in first.co_consts if isinstance(c, types.CodeType))
    second_owner = next(c for c in second.co_consts if isinstance(c, types.CodeType))
    assert first_owner.co_filename != second_owner.co_filename
    assert attestation.owner_code_fingerprint(first_owner) == (
        attestation.owner_code_fingerprint(second_owner)
    )
    assert attestation.CODE_FINGERPRINT_EXCLUDED_FIELDS == ("co_filename",)


def test_nested_code_objects_are_recursed_into_the_fingerprint() -> None:
    outer = compile(
        "def owner(store):\n    def inner():\n        return 1\n    return inner()\n",
        "<x>",
        "exec",
    )
    changed = compile(
        "def owner(store):\n    def inner():\n        return 2\n    return inner()\n",
        "<x>",
        "exec",
    )
    outer_owner = next(c for c in outer.co_consts if isinstance(c, types.CodeType))
    changed_owner = next(c for c in changed.co_consts if isinstance(c, types.CodeType))
    assert outer_owner.co_code == changed_owner.co_code
    assert attestation.owner_code_fingerprint(outer_owner) != (
        attestation.owner_code_fingerprint(changed_owner)
    )


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (True, 1),
        (1, 1.0),
        (0.0, -0.0),
        ("a", b"a"),
        ((1,), [1] and (1.0,)),
        (frozenset({1, 2}), frozenset({1, 3})),
    ],
)
def test_constant_encoding_keeps_distinct_values_distinct(left: object, right: object) -> None:
    assert attestation._encode_constant(left) != attestation._encode_constant(right)


def test_frozenset_constants_encode_without_hash_seed_dependence() -> None:
    value = frozenset({"alpha", "beta", "gamma", 1, 2, 3})
    assert attestation._encode_constant(value) == attestation._encode_constant(
        frozenset(reversed(list(value)))
    )


def test_unsupported_constant_kind_refuses_instead_of_hashing_an_address() -> None:
    with pytest.raises(
        attestation.RuntimeOwnerAttestationError, match="unsupported code constant kind"
    ):
        attestation._encode_constant(object())


def test_value_fingerprint_never_hashes_an_unstable_identity() -> None:
    assert attestation.value_fingerprint(object()) == (
        attestation.UNSTABLE_VALUE_FINGERPRINT
    )
    assert attestation.value_fingerprint(None) != attestation.value_fingerprint(())
    assert attestation.value_fingerprint((1,)) != attestation.value_fingerprint((2,))


# ---------------------------------------------------------------------------
# Negative control: a clean effective binding attests
# ---------------------------------------------------------------------------


def test_clean_production_bindings_pass_runtime_attestation() -> None:
    measured = _attest(production, _production_expectations())
    assert measured.conforms is True
    assert measured.reasons == ()
    assert len(measured.owners) == 11
    assert [row.owner for row in measured.owners] == sorted(
        attestation.FROZEN_REPLAY_OWNERS
    )


def test_clean_replica_bindings_pass_runtime_attestation(replica: types.ModuleType) -> None:
    measured = _attest(replica, _replica_expectations(replica))
    assert measured.conforms is True
    assert measured.reasons == ()


def test_attestation_is_independent_of_ambient_decimal_context() -> None:
    expectations = _production_expectations()
    baseline = _attest(production, expectations).digest
    with decimal.localcontext() as context:
        context.prec = 3
        context.rounding = decimal.ROUND_UP
        context.Emin = -9
        context.Emax = 9
        assert _attest(production, expectations).digest == baseline


# ---------------------------------------------------------------------------
# Required adversarial runtime regressions
# ---------------------------------------------------------------------------


def _replacement(module: types.ModuleType) -> types.FunctionType:
    def replacement(*args: object, **kwargs: object) -> dict[str, object]:
        return {"substituted": True}

    return replacement


def test_module_dictionary_owner_substitution_refuses(replica: types.ModuleType) -> None:
    expectations = _replica_expectations(replica)
    assert _attest(replica, expectations).conforms is True
    sys.modules[replica.__name__].__dict__["_verify_schedule"] = _replacement(replica)
    assert "OWNER_CODE_FINGERPRINT_MISMATCH" in _reasons_for(
        replica, expectations, "_verify_schedule"
    )
    _refuses_epoch(replica, expectations, "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")


def test_direct_dunder_setattr_code_mutation_refuses(replica: types.ModuleType) -> None:
    expectations = _replica_expectations(replica)
    owner = replica.__dict__["_verify_venue_row"]
    owner.__setattr__("__code__", _replacement(replica).__code__)
    assert _reasons_for(replica, expectations, "_verify_venue_row") == (
        "OWNER_CODE_FINGERPRINT_MISMATCH",
    )
    _refuses_epoch(replica, expectations, "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")


def test_object_setattr_code_mutation_refuses(replica: types.ModuleType) -> None:
    expectations = _replica_expectations(replica)
    owner = replica.__dict__["venue_session_status"]
    object.__setattr__(owner, "__code__", _replacement(replica).__code__)
    assert _reasons_for(replica, expectations, "venue_session_status") == (
        "OWNER_CODE_FINGERPRINT_MISMATCH",
    )
    _refuses_epoch(replica, expectations, "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")


def test_type_setattr_code_mutation_refuses(replica: types.ModuleType) -> None:
    expectations = _replica_expectations(replica)
    owner = replica.__dict__["common_etf_session_status"]
    type(owner).__setattr__(owner, "__code__", _replacement(replica).__code__)
    assert _reasons_for(replica, expectations, "common_etf_session_status") == (
        "OWNER_CODE_FINGERPRINT_MISMATCH",
    )
    _refuses_epoch(replica, expectations, "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")


def test_same_code_with_foreign_globals_refuses(replica: types.ModuleType) -> None:
    """``types.FunctionType(expected_code, attacker_globals)`` matches the bytes."""

    expectations = _replica_expectations(replica)
    original = replica.__dict__["derive_etf_window_calendar"]
    foreign_globals = dict(replica.__dict__)
    rebuilt = types.FunctionType(
        original.__code__,
        foreign_globals,
        original.__name__,
        original.__defaults__,
        original.__closure__,
    )
    rebuilt.__qualname__ = original.__qualname__
    rebuilt.__module__ = original.__module__
    rebuilt.__kwdefaults__ = original.__kwdefaults__
    replica.__dict__["derive_etf_window_calendar"] = rebuilt
    reasons = _reasons_for(replica, expectations, "derive_etf_window_calendar")
    assert reasons == ("OWNER_GLOBALS_NAMESPACE_MISMATCH",)
    assert attestation.owner_code_fingerprint(rebuilt.__code__) == next(
        row.code_fingerprint
        for row in expectations
        if row.owner == "derive_etf_window_calendar"
    )
    _refuses_epoch(replica, expectations, "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")


def test_changed_defaults_refuse_although_the_code_is_identical(
    replica: types.ModuleType,
) -> None:
    expectations = _replica_expectations(replica)
    owner = replica.__dict__["expected_etf_publication_dates"]
    owner.__defaults__ = ("injected",)
    assert _reasons_for(replica, expectations, "expected_etf_publication_dates") == (
        "OWNER_DEFAULTS_FINGERPRINT_MISMATCH",
    )
    _refuses_epoch(replica, expectations, "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")


def test_changed_kwdefaults_refuse_although_the_code_is_identical(
    replica: types.ModuleType,
) -> None:
    expectations = _replica_expectations(replica)
    owner = replica.__dict__["scientific_etf_flow_window"]
    owner.__kwdefaults__ = {"injected": 1}
    assert _reasons_for(replica, expectations, "scientific_etf_flow_window") == (
        "OWNER_KWDEFAULTS_FINGERPRINT_MISMATCH",
    )
    _refuses_epoch(replica, expectations, "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")


def test_closure_substitution_refuses(replica: types.ModuleType) -> None:
    expectations = _replica_expectations(replica)
    original = replica.__dict__["validate_normalized_schedule_against_source"]

    def factory(captured: object) -> types.FunctionType:
        def shadow(store: object, normalized_schedule_sha256: str) -> object:
            return captured

        return shadow

    celled = factory("captured")
    replica.__dict__["validate_normalized_schedule_against_source"] = celled
    reasons = _reasons_for(
        replica, expectations, "validate_normalized_schedule_against_source"
    )
    assert "OWNER_CLOSURE_CONTRACT_MISMATCH" in reasons
    assert original.__closure__ is None
    _refuses_epoch(replica, expectations, "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")


@pytest.mark.parametrize("kind", ["partial", "wrapper", "callable_object", "bound_method"])
def test_callable_substitution_that_behaves_equivalently_refuses(
    replica: types.ModuleType, kind: str
) -> None:
    expectations = _replica_expectations(replica)
    original = replica.__dict__["_verify_schedule_record"]

    class Equivalent:
        def __call__(self, *args: object, **kwargs: object) -> object:
            return original(*args, **kwargs)

        def bound(self, *args: object, **kwargs: object) -> object:
            return original(*args, **kwargs)

    if kind == "partial":
        substitute: object = functools.partial(original)
    elif kind == "wrapper":

        @functools.wraps(original)
        def wrapper(*args: object, **kwargs: object) -> object:
            return original(*args, **kwargs)

        substitute = wrapper
    elif kind == "callable_object":
        substitute = Equivalent()
    else:
        substitute = Equivalent().bound

    replica.__dict__["_verify_schedule_record"] = substitute
    reasons = _reasons_for(replica, expectations, "_verify_schedule_record")
    if kind == "wrapper":
        assert "OWNER_WRAPPER_STATE_MISMATCH" in reasons
        assert "OWNER_CODE_FINGERPRINT_MISMATCH" in reasons
    else:
        assert reasons == ("OWNER_CALLABLE_TYPE_MISMATCH",)
    _refuses_epoch(replica, expectations, "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")


def test_deleted_owner_binding_refuses(replica: types.ModuleType) -> None:
    expectations = _replica_expectations(replica)
    del replica.__dict__["venue_session_calendar_record"]
    assert _reasons_for(replica, expectations, "venue_session_calendar_record") == (
        "OWNER_BINDING_ABSENT",
    )
    _refuses_epoch(replica, expectations, "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")


def test_module_unbound_from_sys_modules_refuses(replica: types.ModuleType) -> None:
    expectations = _replica_expectations(replica)
    sys.modules[replica.__name__] = types.ModuleType(replica.__name__)
    measured = _attest(replica, expectations)
    assert "MODULE_NOT_BOUND_IN_SYS_MODULES" in measured.namespace_reasons
    assert measured.conforms is False
    _refuses_epoch(replica, expectations, "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")


def test_replaced_namespace_builtins_refuses(replica: types.ModuleType) -> None:
    expectations = _replica_expectations(replica)
    replica.__dict__["__builtins__"] = dict(
        vars(__import__("builtins")), len=lambda value: 0
    )
    measured = _attest(replica, expectations)
    assert "MODULE_NAMESPACE_BUILTINS_MISMATCH" in measured.namespace_reasons
    assert measured.conforms is False
    _refuses_epoch(replica, expectations, "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")


def test_mutation_syntax_is_irrelevant_to_the_proof(replica: types.ModuleType) -> None:
    """Four different substitution mechanisms produce one identical refusal."""

    expectations = _replica_expectations(replica)
    replacement_code = _replacement(replica).__code__
    owners = (
        "_verify_schedule",
        "_verify_venue_row",
        "venue_session_status",
        "common_etf_session_status",
    )
    sys.modules[replica.__name__].__dict__[owners[0]].__code__ = replacement_code
    replica.__dict__[owners[1]].__setattr__("__code__", replacement_code)
    object.__setattr__(replica.__dict__[owners[2]], "__code__", replacement_code)
    target = replica.__dict__[owners[3]]
    type(target).__setattr__(target, "__code__", replacement_code)
    measured = _attest(replica, expectations)
    refused = {
        row.owner: row.reasons for row in measured.owners if not row.conforms
    }
    assert set(refused) == set(owners)
    assert set(refused.values()) == {("OWNER_CODE_FINGERPRINT_MISMATCH",)}


# ---------------------------------------------------------------------------
# Scientific execution epoch
# ---------------------------------------------------------------------------


def test_clean_epoch_admits_the_result_and_records_evidence() -> None:
    expectations = _production_expectations()
    events: list[str] = []

    def operation(module: types.ModuleType) -> str:
        events.append("operation")
        assert module is production
        return "scientific-result"

    def admit(result: str) -> str:
        events.append("admit")
        return f"admitted:{result}"

    outcome = attestation.run_scientific_execution_epoch(
        _epoch(production, expectations), operation, admit
    )
    assert events == ["operation", "admit"]
    assert outcome.admitted is True
    assert outcome.attestation_match is True
    assert outcome.result == "admitted:scientific-result"
    assert outcome.pre_attestation_digest == outcome.post_attestation_digest
    assert sorted(outcome.evidence) == sorted(attestation.ATTESTATION_EVIDENCE_FIELDS)
    assert outcome.evidence["failure_reason"] is None
    assert outcome.evidence["result_admitted"] is True
    assert outcome.evidence["decision_time"] == "2026-09-19T00:00:00Z"


def test_pre_attestation_failure_never_calls_the_owner_operation(
    replica: types.ModuleType,
) -> None:
    expectations = _replica_expectations(replica)
    replica.__dict__["_verify_schedule"] = _replacement(replica)
    calls: list[str] = []

    def operation(module: types.ModuleType) -> str:
        calls.append("operation")
        return "result"

    with pytest.raises(
        attestation.RuntimeOwnerAttestationError,
        match="SCIENTIFIC_EXECUTION_NOT_AUTHORIZED",
    ) as excinfo:
        attestation.run_scientific_execution_epoch(
            _epoch(replica, expectations), operation, lambda result: result
        )
    assert calls == []
    evidence = excinfo.value.evidence
    assert evidence["result_admitted"] is False
    assert evidence["attestation_match"] is False
    assert evidence["post_owner_attestation_digest"] is None
    assert evidence["failure_reason"].startswith("SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")


def test_mutation_between_pre_and_post_rejects_the_result(
    replica: types.ModuleType,
) -> None:
    expectations = _replica_expectations(replica)
    events: list[str] = []

    def operation(module: types.ModuleType) -> str:
        events.append("operation")
        module.__dict__["venue_session_status"] = _replacement(module)
        return "scientific-result"

    def admit(result: str) -> str:  # pragma: no cover - must never run
        events.append("admit")
        return result

    with pytest.raises(
        attestation.RuntimeOwnerAttestationError, match="RESULT_REJECTED"
    ) as excinfo:
        attestation.run_scientific_execution_epoch(
            _epoch(replica, expectations), operation, admit
        )
    assert events == ["operation"]
    evidence = excinfo.value.evidence
    assert evidence["attestation_match"] is False
    assert evidence["result_admitted"] is False
    assert evidence["pre_owner_attestation_digest"] != (
        evidence["post_owner_attestation_digest"]
    )
    assert "DATA_QUALITY_FAIL" in evidence["failure_reason"]


def test_result_admission_strictly_follows_post_attestation() -> None:
    ordering = attestation.verify_result_admission_ordering()
    assert ordering["post_attestation_precedes_admission"] is True
    assert ordering["persist_then_discover_mismatch"] is False
    assert ordering["exception_path_sweeps_for_drift"] is True
    assert (
        ordering["pre_attestation_line"]
        < ordering["operation_line"]
        < ordering["lazy_result_guard_line"]
        <= ordering["post_attestation_line"]
        < ordering["mismatch_refusal_line"]
        < ordering["admission_line"]
        < ordering["exception_path_drift_sweep_line"]
    )


def test_execution_epochs_are_serialized_and_refuse_reentrancy() -> None:
    expectations = _production_expectations()

    def nested(module: types.ModuleType) -> str:
        attestation.run_scientific_execution_epoch(
            _epoch(production, expectations, "epoch-nested"), lambda inner: "inner"
        )
        return "outer"

    with pytest.raises(
        attestation.RuntimeOwnerAttestationError,
        match="REENTRANT_OR_NESTED_SCIENTIFIC_EXECUTION_EPOCH_REFUSES",
    ):
        attestation.run_scientific_execution_epoch(
            _epoch(production, expectations, "epoch-outer"), nested
        )
    assert getattr(attestation._EPOCH_STATE, "active", False) is False
    assert attestation._EPOCH_SERIALIZATION_LOCK.locked() is False


def test_concurrent_epochs_do_not_overlap() -> None:
    expectations = _production_expectations()
    overlap = []
    inside = threading.Semaphore(1)

    def operation(module: types.ModuleType) -> str:
        acquired = inside.acquire(blocking=False)
        overlap.append(acquired)
        if acquired:
            inside.release()
        return "result"

    threads = [
        threading.Thread(
            target=attestation.run_scientific_execution_epoch,
            args=(_epoch(production, expectations, f"epoch-{index}"), operation),
        )
        for index in range(4)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert overlap == [True, True, True, True]


def test_attesting_one_module_and_executing_another_is_refused(
    replica: types.ModuleType,
) -> None:
    """The epoch binds execution to the very module object it attested."""

    expectations = _replica_expectations(replica)
    executed: list[str] = []

    def operation(module: types.ModuleType) -> str:
        executed.append(module.__name__)
        assert module is replica
        return "result"

    outcome = attestation.run_scientific_execution_epoch(
        _epoch(replica, expectations), operation
    )
    assert executed == [replica.__name__]
    assert outcome.evidence["module_identity"]["module_name"] == replica.__name__
    foreign = types.ModuleType("foreign_calendar")
    foreign.__file__ = str(ROOT / "README.md")
    with pytest.raises(
        attestation.RuntimeOwnerAttestationError, match="MODULE_SOURCE_IDENTITY_MISMATCH"
    ):
        attestation.run_scientific_execution_epoch(
            _epoch(foreign, expectations), operation
        )


def test_epoch_evidence_persists_no_object_address() -> None:
    expectations = _production_expectations()
    outcome = attestation.run_scientific_execution_epoch(
        _epoch(production, expectations), lambda module: "result"
    )
    rendered = json.dumps(outcome.evidence, sort_keys=True)
    assert "0x" not in rendered
    assert " object at " not in rendered
    assert str(id(production)) not in rendered
    for owner in attestation.FROZEN_REPLAY_OWNERS:
        assert str(id(production.__dict__[owner])) not in rendered


def test_attestation_digest_is_stable_across_repeated_measurement() -> None:
    expectations = _production_expectations()
    digests = {_attest(production, expectations).digest for _ in range(5)}
    assert len(digests) == 1


# ---------------------------------------------------------------------------
# Startup attestation
# ---------------------------------------------------------------------------


def test_startup_attestation_refuses_a_wrong_proof_architecture_authority() -> None:
    with pytest.raises(
        attestation.RuntimeOwnerAttestationError,
        match="startup proof-architecture authority mismatch",
    ):
        attestation.attest_scientific_process_startup(
            production, proof_architecture_sha256="0" * 64
        )


def test_startup_attestation_refuses_a_wrong_trusted_persistence_dependency() -> None:
    decision = attestation.runtime_owner_attestation_v1_definition()
    with pytest.raises(
        attestation.RuntimeOwnerAttestationError,
        match="startup trusted-persistence dependency mismatch",
    ):
        attestation.attest_scientific_process_startup(
            production,
            proof_architecture_sha256=decision["definition_sha256"],
            trusted_persistence_sha256="1" * 64,
        )


def test_startup_attestation_still_refuses_current_production_direct_bodies() -> None:
    decision = attestation.runtime_owner_attestation_v1_definition()
    with pytest.raises(
        attestation.RuntimeOwnerAttestationError,
        match="exact dependency ast.Call missing",
    ):
        attestation.attest_scientific_process_startup(
            production, proof_architecture_sha256=decision["definition_sha256"]
        )


def test_startup_attestation_does_not_replace_per_epoch_attestation() -> None:
    rule = attestation.scientific_execution_epoch_rule()
    assert rule["startup_attestation_required"] is True
    assert rule["startup_attestation_replaces_per_epoch_attestation"] is False
    assert attestation.direct_body_dependency_rule()[
        "startup_check_replaces_per_epoch_attestation"
    ] is False


# ---------------------------------------------------------------------------
# Preserved compiled root witness, AST grammar, census and graph
# ---------------------------------------------------------------------------


def test_compiled_root_binding_witness_is_preserved_and_freshly_parent_bound() -> None:
    child = attestation.compiled_root_binding_witness_rule()
    assert child["reused_mechanism"] == "ETF_CALENDAR_COMPILED_BINDING_WITNESS_V1"
    assert child["reused_mechanism_parent_certified_by_this_decision"] is False
    assert child["failed_reused_mechanism_parent_sha256"] == (
        "b5ca36bfa9b96970b667cc44b10c5c5da7eb5ce7c57e5739601640d9b2a8abe9"
    )
    assert child["root_may_be_a_cell_variable_of_the_owner"] is False
    assert child["instruction_scan_deoptimizes_specialized_instructions"] is True
    assert child["proves_which_callable_the_owner_name_denotes_at_runtime"] is False
    assert child["frozen_opcode_numbers"] == dict(sorted(pad2.FROZEN_OPCODE_NUMBERS.items()))


def test_root_cell_prohibition_still_refuses_a_captured_root() -> None:
    source = (
        "def owner(store: CalendarEvidenceStore):\n"
        "    return [store.get(x) for x in ()] and (store.get(y) for y in ())\n"
    )
    findings = attestation.compiled_root_binding_witness(source, OWNER, "<candidate>")
    assert [row.kind for row in findings.root_capture_findings] == [
        "OWNER_ROOT_IS_CELL_VARIABLE"
    ]


def test_typealias_and_definition_time_mutation_detection_are_preserved() -> None:
    alias = (
        "def owner(store: CalendarEvidenceStore):\n"
        "    type Alias = store\n"
        "    return store.get('a')\n"
    )
    assert attestation.compiled_root_binding_witness(
        alias, OWNER, "<candidate>"
    ).findings


def test_closed_ast_store_use_grammar_is_preserved() -> None:
    grammar = attestation.store_root_and_direct_use_grammar()
    assert grammar["normal_form"] == "DIRECT_IMMUTABLE_STORE_PARAMETER_NORMAL_FORM"
    for field in (
        "transparent_aliases_permitted",
        "annotated_store_varargs_permitted",
        "annotated_store_kwargs_permitted",
        "starred_store_forwarding_permitted",
        "nested_annotated_owners_permitted",
        "nested_store_capture_permitted",
        "bound_method_store_extraction_permitted",
        "unknown_store_forwarding_permitted",
        "capability_escape_permitted",
        "private_authoritative_state_access_permitted",
    ):
        assert grammar[field] is False
    assert grammar["documented_apis"] == ["put", "get", "records", "envelopes"]


@pytest.mark.parametrize(
    "body",
    [
        "    alias = store\n    return alias.get('a')\n",
        "    return [store][0].get('a')\n",
        "    return store.get\n",
        "    return (lambda: store.get('a'))()\n",
        "    return store._records\n",
    ],
)
def test_capability_escapes_remain_refused(body: str) -> None:
    source = f"def owner(store: CalendarEvidenceStore):\n{body}"
    with pytest.raises(narrow.NormalFormError):
        narrow.audit_store_capability_normal_form(source, OWNER)


def test_owner_census_is_exactly_eleven_frozen_discovered_and_attested() -> None:
    frozen = tuple(sorted(attestation.FROZEN_REPLAY_OWNERS))
    discovered = tuple(sorted(narrow.discover_replay_owners(CALENDAR_SOURCE_TEXT)))
    attested = tuple(
        sorted(row.owner for row in _attest(production, _production_expectations()).owners)
    )
    assert len(frozen) == len(discovered) == len(attested) == 11
    assert frozen == discovered == attested


def test_replay_owner_graph_closure_is_preserved() -> None:
    rule = attestation.replay_owner_graph_rule()
    assert rule["cycles_permitted"] is False
    assert rule["every_owner_path_terminates_at_documented_store_api"] is True
    assert rule["documented_terminals"] == ["put", "get", "records", "envelopes"]
    assert rule["both_layers_required"] is True
    assert rule["either_layer_substitutes_for_the_other"] is False
    conforming = (
        "def leaf(store: CalendarEvidenceStore):\n"
        "    return store.get('a')\n"
        "def root(store: CalendarEvidenceStore):\n"
        "    return leaf(store)\n"
    )
    edges = narrow.audit_replay_owner_graph(conforming, ("leaf", "root"))
    assert {edge.kind for edge in edges} == {
        "DOCUMENTED_STORE_API_TERMINAL",
        "ENUMERATED_REPLAY_OWNER_EDGE",
    }
    cyclic = (
        "def a(store: CalendarEvidenceStore):\n    return b(store)\n"
        "def b(store: CalendarEvidenceStore):\n    return a(store)\n"
    )
    with pytest.raises(narrow.NormalFormError):
        narrow.audit_replay_owner_graph(cyclic, ("a", "b"))


def test_direct_body_dependency_rule_is_preserved() -> None:
    rule = attestation.direct_body_dependency_rule()
    assert rule["required_direct_bodies"] == [
        "CalendarEvidenceStore.put",
        "CalendarEvidenceStore.get",
        "CalendarEvidenceStore.records",
        "CalendarEvidenceStore.envelopes",
        "collect_official_calendar",
    ]
    assert rule["wrapper_installed_guards_permitted"] is False
    assert rule["wrapper_installer_must_be_removed"] == "_install_exact_dependency_guards"
    assert rule["wrapper_removal_is_independent_of_module_owner_attestation"] is True


# ---------------------------------------------------------------------------
# Demoted static reflection policy and namespace reach classification
# ---------------------------------------------------------------------------


def test_static_reflection_blacklist_is_not_owner_identity_proof() -> None:
    child = attestation.static_reflection_policy_demotion()
    assert child["frozen_finding"] == (
        "STATIC_REFLECTION_BLACKLIST_IS_NOT_OWNER_IDENTITY_PROOF"
    )
    assert child["reflection_blacklist_complete"] is False
    assert child["static_reflection_blacklist_is_scientific_completeness_authority"] is False
    assert child["retained_roles"] == [
        "DIAGNOSTIC",
        "DEFENCE_IN_DEPTH",
        "CODING_POLICY_ENFORCEMENT",
    ]
    assert child["enumerating_more_reflection_names_is_a_valid_correction"] is False
    assert child["detection_requires_knowing_how_the_mutation_was_performed"] is False


def test_four_artifact_builder_sites_are_read_only_dispatch() -> None:
    classification = attestation.classify_module_namespace_reach_sites(
        CALENDAR_SOURCE_TEXT
    )
    assert classification["reach_scopes"] == [
        "_children",
        "_install_exact_dependency_guards",
        "_semantic_ast_sha256",
        "restore_artifacts",
        "write_artifacts",
    ]
    assert classification["namespace_write_scopes"] == [
        "_install_exact_dependency_guards"
    ]
    assert classification["written_keys"] == ["collect_official_calendar"]
    assert classification["frozen_owner_bindings_written"] == []
    assert classification["unclassified_reach_scopes"] == []
    assert classification["rewrite_required_solely_by_owner_identity"] == []
    assert classification["artifact_builder_dispatch_scopes"] == [
        "_children",
        "_semantic_ast_sha256",
        "restore_artifacts",
        "write_artifacts",
    ]


def test_artifact_generation_does_not_change_any_effective_owner_binding(
    tmp_path: Path,
) -> None:
    """Empirical half of the §36 classification, on the real production module."""

    expectations = _production_expectations()
    before = _attest(production, expectations)
    assert before.conforms is True
    production.write_artifacts(tmp_path / "artifacts")
    production.restore_artifacts(tmp_path / "artifacts")
    production._semantic_ast_sha256()
    production._children()
    after = _attest(production, expectations)
    assert after.conforms is True
    assert after.digest == before.digest


def test_a_namespace_write_to_a_frozen_owner_would_be_reported() -> None:
    source = (
        "def owner(store: CalendarEvidenceStore):\n    return store.get('a')\n"
        "def rebind():\n    globals()['owner'] = None\n"
    )
    classification = attestation.classify_module_namespace_reach_sites(source, OWNER)
    assert classification["frozen_owner_bindings_written"] == ["owner"]
    assert classification["rewrite_required_solely_by_owner_identity"] == ["rebind"]


def test_an_unclassified_namespace_reach_is_reported() -> None:
    source = (
        "def owner(store: CalendarEvidenceStore):\n    return store.get('a')\n"
        "def sneaky(key):\n    globals()[key] = None\n"
    )
    classification = attestation.classify_module_namespace_reach_sites(source, OWNER)
    assert classification["unclassified_reach_scopes"] == ["sneaky"]
    assert classification["rewrite_required_solely_by_owner_identity"] == ["sneaky"]


# ---------------------------------------------------------------------------
# Threat model, current production and lineage
# ---------------------------------------------------------------------------


def test_threat_model_is_preserved_and_never_silently_strengthened() -> None:
    boundary = attestation.trusted_process_boundary_reference()
    assert boundary["production_python_process_trusted"] is True
    assert boundary["hostile_same_process_mutation_resistance_required"] is False
    assert boundary["project_owned_scientific_bypasses_in_scope"] is True
    assert boundary["arbitrary_hostile_in_process_manipulation_in_scope"] is False
    assert boundary["arbitrary_debugger_memory_or_interpreter_mutation_in_scope"] is False
    assert boundary["hostile_same_process_resistance_if_later_required"] == (
        "PROCESS_ISOLATION"
    )
    assert boundary["threat_model_changed_by_this_decision"] is False
    assert boundary["transient_mutate_and_restore_resistance_claimed"] is False
    assert boundary["transient_mutate_and_restore_classification"] == (
        "ARBITRARY_ADVERSARIAL_SAME_PROCESS_MUTATION_OUTSIDE_ACCEPTED_TRUST_MODEL"
    )
    assert boundary["transient_mutate_and_restore_limitation_is_explicit"] is True
    assert boundary["escalation_path_is_more_python_reflection_filters"] is False


def test_transient_mutate_and_restore_is_explicitly_not_claimed(
    replica: types.ModuleType,
) -> None:
    """The documented limitation is real, and the decision says so out loud."""

    expectations = _replica_expectations(replica)
    original = replica.__dict__["_verify_schedule"]

    def operation(module: types.ModuleType) -> str:
        module.__dict__["_verify_schedule"] = _replacement(module)
        module.__dict__["_verify_schedule"] = original
        return "result"

    outcome = attestation.run_scientific_execution_epoch(
        _epoch(replica, expectations), operation
    )
    assert outcome.admitted is True
    assert attestation.pre_post_attestation_rule()[
        "transient_mutate_and_restore_inside_one_epoch_detected"
    ] is False
    assert attestation.pre_post_attestation_rule()[
        "transient_mutate_and_restore_escalation"
    ] == "PROCESS_ISOLATION"


def test_current_production_expected_result_is_bound_mechanically() -> None:
    production_result = attestation.verify_current_production_expected_result(
        CALENDAR_SOURCE_TEXT
    )
    assert production_result["root_write_clear_or_delete_findings"] == 0
    assert production_result["root_cell_finding"] == (
        "common_etf_session_status:evidence_store"
    )
    assert production_result["ast_store_use_normal_form"] == (
        "REFUSED_AT_THE_SAME_GENERATOR_CAPTURE"
    )
    assert production_result["calendar_production_conformance"] == "NO"
    assert production_result["calendar_implementation"] == "BLOCKED"
    assert production_result[
        "artifact_builder_dispatch_rewrite_required_solely_by_this_decision"
    ] is False
    assert production_result["wrapper_installer_removal_required"] is True
    assert production_result["direct_dependency_body_findings"]["conforms"] is False
    assert set(production_result["expected_owner_code_fingerprints"]) == set(
        attestation.FROZEN_REPLAY_OWNERS
    )


def test_decision_does_not_certify_current_production() -> None:
    completeness = attestation.proof_order_and_completeness_definition()
    assert completeness["decision_certifies_current_production_conformance"] is False
    assert completeness["decision_certifies_grammar_and_attestation_mechanism"] is True
    assert completeness["static_module_owner_identity_proof"] is False
    assert completeness["guarantee_excludes"] == [
        "TRANSIENT_MUTATE_AND_PERFECTLY_RESTORE_INSIDE_ONE_EPOCH",
        "ARBITRARY_HOSTILE_SAME_PROCESS_ACTORS",
        "DEBUGGER_FRAME_OR_INTERPRETER_MEMORY_MUTATION",
    ]


def test_failed_and_calendar_lineages_are_preserved_unchanged() -> None:
    assert attestation.FAILED_ARCHITECTURE_LINEAGE == (
        "0c237c1b217b1fd406ec3967309774293c01d3e27574b9f4a7d1b9a0e887b55d",
        "a7d2b08741080494cc4ca0269bf21e28e631c7f2e70887bcb0e1beb302534dd0",
        "dc36ffe228b7a3bc6d9145042b4e301c8624c99a79d71a88b46fc268f1372c3e",
        "9f6af1794e8b49dce38288b9f1b9710bffd04ba70303b5c380e8fb447ac86295",
        "7ef114fede9efebe594f0ecf119d097a1161119f448737d0df10afdf9468d17b",
        "b5ca36bfa9b96970b667cc44b10c5c5da7eb5ce7c57e5739601640d9b2a8abe9",
    )
    assert attestation.FAILED_CALENDAR_LINEAGE == (
        "a1ceb66bc0f6b90066d3da123447ae6e7dd983047adf363790336bfb557db0b9",
        "b81c1702c65e1e042b7a2f948216305618fd21fabe2e629edc46376882b357af",
        "0524334396e529afbd057db25721b92c3074dd10205dd08be0946e512f99c855",
        "b499c6a4d1a8a6c25c6b108279831f26508742de97bdbcd57c7bee58e584e076",
        "901f572e03781030906cd6fe72a73ec5804f9ffbdefe6a8a944c067f7fd9853f",
    )
    science = attestation.science_lineage_and_safety()
    assert science["preserved_hashes"] == {
        "certified_prospective_v1": (
            "8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7"
        ),
        "failed_prospective_v2": (
            "488251df7bc1b49f801caa0dc28eb5224836574b154db9e4a70d4be670ec0b6d"
        ),
    }
    assert science["certified_dependency"]["definition_sha256"] == (
        "02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772"
    )
    assert science["certified_dependency"]["changed"] is False
    assert science["certified_dependency"]["rereviewed_wholesale_by_this_decision"] is False
    assert all(
        row["failed"] and not row["certified"] and not row["used"]
        and row["prospective_observations"] == 0
        for row in science["failed_architecture_lineage"]
    )
    assert science["safety"] == {
        "prospective_observations": 0,
        "real_stage_b_evaluation": False,
        "collection_authorized": False,
        "calendar_certified": False,
        "calendar_implementation": "BLOCKED_PENDING_REVIEW_PASS",
        "postp1_001v2r1": "BLOCKED",
        "postp1_003r3": "BLOCKED",
        "postp1_004": "BLOCKED",
        "btc019": "UNTOUCHED",
        "epic_t": "UNCHANGED",
        "trusted_persistence": "CLOSED_UNCHANGED",
    }


def test_failed_pad2_artifacts_are_not_mutated() -> None:
    failed_dir = ROOT / pad2.OUTPUT_NAMESPACE
    assert pad2.restore_artifacts(failed_dir)["definition_sha256"] == (
        "b5ca36bfa9b96970b667cc44b10c5c5da7eb5ce7c57e5739601640d9b2a8abe9"
    )
    assert failed_dir != ARTIFACT_DIR


def test_calendar_production_source_is_unchanged_by_this_decision() -> None:
    assert attestation.source_sha256(CALENDAR_SOURCE_TEXT) == (
        attestation.runtime_owner_attestation_v1_definition()[
            "current_production_expected_result"
        ]["reviewed_source_sha256"]
    )
    science = attestation.science_lineage_and_safety()["preserved_science"]
    assert science["etf_calendar_production_code_changed_by_this_decision"] is False
    assert science[
        "source_urls_profiles_tls_redirects_parsers_coverage_early_closes"
    ] == "UNCHANGED"
    assert science["pit_common_session_etf_formulas_revision_semantics"] == "UNCHANGED"
    assert science["stage_b_metrics_risk_stops_thresholds"] == "UNCHANGED"


# ---------------------------------------------------------------------------
# Material mutation sensitivity, artifacts and determinism
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("builder", "field"),
    [
        ("pre_post_attestation_rule", "pre_execution_attestation_required"),
        ("pre_post_attestation_rule", "post_execution_attestation_required"),
        ("pre_post_attestation_rule", "post_attestation_before_result_admission"),
        (
            "runtime_owner_identity_contract",
            "globals_must_be_the_attested_module_namespace",
        ),
        ("runtime_owner_identity_contract", "code_execution_fingerprint_exact"),
        ("runtime_owner_identity_contract", "defaults_attested"),
        ("runtime_owner_identity_contract", "kwdefaults_attested"),
        ("runtime_owner_identity_contract", "closure_contract"),
        ("static_reflection_policy_demotion", "reflection_blacklist_complete"),
        (
            "compiled_root_binding_witness_rule",
            "root_may_be_a_cell_variable_of_the_owner",
        ),
        ("direct_body_dependency_rule", "required_direct_bodies"),
        (
            "trusted_process_boundary_reference",
            "hostile_same_process_resistance_if_later_required",
        ),
        ("owner_code_fingerprint_definition", "scalar_fields"),
        ("scientific_execution_epoch_rule", "epoch_order"),
        ("attestation_evidence_schema", "fields"),
        ("module_namespace_reach_site_classification", "artifact_builder_dispatch_sites"),
        ("replay_owner_graph_rule", "cycles_permitted"),
        ("proof_order_and_completeness_definition", "proof_order"),
        ("store_root_and_direct_use_grammar", "documented_apis"),
        ("proof_interpreter_identity", "frozen_identity"),
        ("science_lineage_and_safety", "failed_calendar_lineage"),
    ],
)
def test_material_mutations_move_child_and_parent_hash(builder: str, field: str) -> None:
    original_child = getattr(attestation, builder)()
    payload = copy.deepcopy(original_child)
    payload.pop("definition_sha256")
    value = payload[field]
    if isinstance(value, list):
        value.append("MUTATED")
    elif isinstance(value, dict):
        value["MUTATED"] = True
    elif isinstance(value, bool):
        payload[field] = not value
    else:
        payload[field] = f"{value}_MUTATED"
    mutated_child = attestation._definition(payload)
    assert mutated_child["definition_sha256"] != original_child["definition_sha256"]
    parent = attestation.runtime_owner_attestation_v1_definition()
    parent_payload = copy.deepcopy(parent)
    parent_payload.pop("definition_sha256")
    parent_payload["child_definition_sha256"][builder] = mutated_child["definition_sha256"]
    assert attestation._definition(parent_payload)["definition_sha256"] != (
        parent["definition_sha256"]
    )


def test_removing_a_closure_contract_moves_the_child_hash() -> None:
    original = attestation.runtime_owner_identity_contract()
    payload = copy.deepcopy(original)
    payload.pop("definition_sha256")
    payload.pop("closure_contract")
    assert attestation._definition(payload)["definition_sha256"] != (
        original["definition_sha256"]
    )


def test_removing_the_process_isolation_escalation_moves_the_child_hash() -> None:
    original = attestation.trusted_process_boundary_reference()
    payload = copy.deepcopy(original)
    payload.pop("definition_sha256")
    payload.pop("hostile_same_process_resistance_if_later_required")
    assert attestation._definition(payload)["definition_sha256"] != (
        original["definition_sha256"]
    )


def test_artifacts_reproduce_under_child_order_and_tampering_refuses(
    tmp_path: Path,
) -> None:
    assert attestation.restore_artifacts(ARTIFACT_DIR) == (
        attestation.runtime_owner_attestation_v1_definition()
    )
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first = attestation.write_artifacts(first_dir)
    second = attestation.write_artifacts(
        second_dir, tuple(reversed(attestation._CHILD_ARTIFACTS))
    )
    assert first == second
    assert {path.name: path.read_bytes() for path in first_dir.iterdir()} == {
        path.name: path.read_bytes() for path in second_dir.iterdir()
    }
    child_path = first_dir / "runtime_owner_identity_contract.json"
    child = json.loads(child_path.read_text(encoding="ascii"))
    child["defaults_attested"] = False
    child_path.write_text(
        json.dumps(child, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    with pytest.raises(
        attestation.RuntimeOwnerAttestationError, match="does not reproduce"
    ):
        attestation.restore_artifacts(first_dir)


@pytest.mark.parametrize("seed", ["0", "1", "8675309"])
def test_fresh_process_hashseed_alternate_cwd_and_output_reproduce(
    tmp_path: Path, seed: str
) -> None:
    output = tmp_path / f"seed-{seed}"
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = seed
    environment["PYTHONPATH"] = str(ROOT)
    completed = subprocess.run(
        [
            str(FROZEN_PYTHON),
            "-m",
            "btc_predictor.research.etf_calendar_runtime_owner_attestation",
            str(output),
        ],
        cwd=tmp_path,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    expected = attestation.runtime_owner_attestation_v1_definition()
    assert completed.stdout.strip() == expected["definition_sha256"]
    assert attestation.restore_artifacts(output) == expected


@pytest.mark.parametrize("seed", ["0", "1", "8675309"])
def test_runtime_attestation_digest_reproduces_in_a_fresh_process(seed: str) -> None:
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = seed
    environment["PYTHONPATH"] = str(ROOT)
    program = (
        "from btc_predictor.research import etf_calendar_runtime_owner_attestation as a\n"
        "from btc_predictor.research import etf_publication_calendar as c\n"
        "s = a.CALENDAR_SOURCE.read_text(encoding='utf-8')\n"
        "e = a.expected_owner_identities(s)\n"
        "m = a.attest_runtime_owners(c, e, a.source_sha256(s))\n"
        "assert m.conforms, m.reasons\n"
        "print(m.digest)\n"
    )
    completed = subprocess.run(
        [str(FROZEN_PYTHON), "-c", program],
        cwd=str(ROOT.parent),
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    expected = _attest(production, _production_expectations()).digest
    assert completed.stdout.strip() == expected


# ---------------------------------------------------------------------------
# Transitive execution closure
# ---------------------------------------------------------------------------


def test_execution_closure_is_derived_mechanically_from_the_certified_source() -> None:
    closure = attestation.execution_closure(CALENDAR_SOURCE_TEXT)
    assert set(attestation.FROZEN_REPLAY_OWNERS) <= set(closure.functions)
    assert len(closure.functions) == 25
    assert "CalendarEvidenceStore" in closure.classes
    assert "_semantics" in closure.imports and "_trusted" in closure.imports
    assert "CANONICAL_VENUES" in closure.values
    assert "SOURCE_AUTHORITY_REGISTRY" in closure.values
    assert set(closure.unresolved_names) >= {"isinstance", "sorted", "tuple"}
    expectation = attestation.expected_execution_closure(CALENDAR_SOURCE_TEXT)
    assert all(row.statically_derived for row in expectation.values)
    assert {row.name for row in expectation.imports} == set(closure.imports)
    project = {
        row.certified_module: len(row.function_expectations)
        for row in expectation.imports
        if row.ownership == "PROJECT_OWNED"
    }
    assert project == {
        "btc_predictor.features.flow": 26,
        "btc_predictor.research.etf_calendar_semantics": 13,
        "btc_predictor.research.trusted_acquisition": 10,
        "btc_predictor.data": 1,
    }


def test_closure_attests_the_clean_production_surface_except_the_wrapper_guards() -> None:
    measured = _attest(
        production,
        _production_expectations(),
        attestation.expected_execution_closure(CALENDAR_SOURCE_TEXT),
    )
    assert measured.conforms is False
    assert measured.reasons == (
        "CLOSURE_CLASS:CalendarEvidenceStore:CLOSURE_CLASS_CERTIFIED_METHOD_MISMATCH",
        "CLOSURE_CLASS:CalendarEvidenceStore:CLOSURE_CLASS_METHOD_WRAPPER_STATE_MISMATCH",
    )
    store = next(row for row in measured.closure if row.name == "CalendarEvidenceStore")
    wrappers = dict(store.material)["method_wrapper_states"]
    assert sorted(
        name for name, state in wrappers.items() if state != "UNDECORATED_PLAIN_FUNCTION"
    ) == ["envelopes", "get", "put", "records"]


def _closure_reasons(
    module: types.ModuleType, name: str
) -> tuple[str, ...]:
    measured = _attest(
        module, _replica_expectations(module), _closure_expectations(module)
    )
    return next(row.reasons for row in measured.closure if row.name == name)


def test_private_helper_substitution_refuses_although_every_owner_matches(
    replica: types.ModuleType,
) -> None:
    """The exact defect the owner-only surface could not see."""

    owners = _replica_expectations(replica)
    original = replica.__dict__["_parse_date"]
    def shifted(value: object, field: str) -> object:
        return original(value, field)

    shifted.__name__ = "_parse_date"
    shifted.__qualname__ = "_parse_date"
    shifted.__module__ = replica.__name__
    replica.__dict__["_parse_date"] = shifted
    assert _attest(replica, owners).conforms is True
    assert _closure_reasons(replica, "_parse_date") == (
        "OWNER_CODE_FINGERPRINT_MISMATCH",
        "OWNER_GLOBALS_NAMESPACE_MISMATCH",
        "OWNER_CLOSURE_CONTRACT_MISMATCH",
    )
    _refuses_epoch_with_closure(replica, "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")


def _refuses_epoch_with_closure(module: types.ModuleType, match: str) -> None:
    calls: list[str] = []

    def operation(attested: types.ModuleType) -> str:
        calls.append("operation")
        return "result"

    with pytest.raises(attestation.RuntimeOwnerAttestationError, match=match):
        attestation.run_scientific_execution_epoch(
            _epoch(
                module,
                _replica_expectations(module),
                closure=_closure_expectations(module),
            ),
            operation,
            lambda result: calls.append("admit"),
        )
    assert "admit" not in calls


def test_frozen_constant_mutation_refuses(replica: types.ModuleType) -> None:
    owners = _replica_expectations(replica)
    replica.__dict__["CANONICAL_VENUES"] = (
        *replica.__dict__["CANONICAL_VENUES"],
        "ROGUE_VENUE",
    )
    assert _attest(replica, owners).conforms is True
    assert _closure_reasons(replica, "CANONICAL_VENUES") == (
        "CLOSURE_VALUE_FINGERPRINT_MISMATCH",
    )
    _refuses_epoch_with_closure(replica, "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")


def test_authority_registry_mutation_refuses(replica: types.ModuleType) -> None:
    registry = replica.__dict__["SOURCE_AUTHORITY_REGISTRY"]
    venue = sorted(registry)[0]
    registry[venue] = dict(registry[venue], source_authority_id="ROGUE_AUTHORITY")
    assert _closure_reasons(replica, "SOURCE_AUTHORITY_REGISTRY") == (
        "CLOSURE_VALUE_FINGERPRINT_MISMATCH",
    )


def test_result_dataclass_substitution_refuses(replica: types.ModuleType) -> None:
    owners = _replica_expectations(replica)

    class VenueSessionResolution:  # noqa: D401 - adversarial substitute
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.venue_id = "EVIL"

    replica.__dict__["VenueSessionResolution"] = VenueSessionResolution
    assert _attest(replica, owners).conforms is True
    reasons = _closure_reasons(replica, "VenueSessionResolution")
    assert "CLOSURE_CLASS_IDENTITY_MISMATCH" in reasons
    _refuses_epoch_with_closure(replica, "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")


def test_error_class_substitution_refuses(replica: types.ModuleType) -> None:
    class EtfCalendarAuthorityError(Exception):  # noqa: N818 - adversarial substitute
        pass

    replica.__dict__["EtfCalendarAuthorityError"] = EtfCalendarAuthorityError
    reasons = _closure_reasons(replica, "EtfCalendarAuthorityError")
    assert "CLOSURE_CLASS_IDENTITY_MISMATCH" in reasons


def test_project_dependency_function_mutation_refuses(
    replica: types.ModuleType,
) -> None:
    """A dependency module's own function is inside the attested closure."""

    owners = _replica_expectations(replica)
    semantics = replica.__dict__["_semantics"]
    original = semantics.reduce_common_session
    try:
        semantics.reduce_common_session = lambda states: "RESOLVED"
        assert _attest(replica, owners).conforms is True
        reasons = _closure_reasons(replica, "_semantics")
        assert reasons == ("CLOSURE_IMPORT_PROJECT_FUNCTION_MISMATCH",)
        _refuses_epoch_with_closure(replica, "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED")
    finally:
        semantics.reduce_common_session = original


def test_project_dependency_source_drift_refuses(replica: types.ModuleType) -> None:
    closure = _closure_expectations(replica)
    drifted = tuple(
        attestation.ClosureImportExpectation(
            name=row.name,
            origin_module=row.origin_module,
            origin_attribute=row.origin_attribute,
            ownership=row.ownership,
            certified_module=row.certified_module,
            source_sha256="0" * 64 if row.name == "_semantics" else row.source_sha256,
            defining_module=row.defining_module,
            function_expectations=row.function_expectations,
        )
        for row in closure.imports
    )
    tampered = attestation.ExecutionClosureExpectation(
        closure=closure.closure,
        owners=closure.owners,
        functions=closure.functions,
        classes=closure.classes,
        values=closure.values,
        imports=drifted,
    )
    measured = _attest(replica, _replica_expectations(replica), tampered)
    assert "CLOSURE_IMPORT:_semantics:CLOSURE_IMPORT_SOURCE_IDENTITY_MISMATCH" in (
        measured.reasons
    )


def test_imported_object_rebinding_refuses(replica: types.ModuleType) -> None:
    replica.__dict__["require_utc_datetime"] = lambda value, field: value
    assert _closure_reasons(replica, "require_utc_datetime") == (
        "CLOSURE_IMPORT_OBJECT_IDENTITY_MISMATCH",
    )


def test_imported_module_rebinding_refuses(replica: types.ModuleType) -> None:
    replica.__dict__["json"] = types.ModuleType("json_impostor")
    reasons = _closure_reasons(replica, "json")
    assert "CLOSURE_IMPORT_ORIGIN_MISMATCH" in reasons


def test_deep_value_fingerprint_is_deterministic_and_injective() -> None:
    left = {"a": [1, 2, {"b": (3, 4)}], "c": frozenset({"x", "y"})}
    right = {"c": frozenset({"y", "x"}), "a": [1, 2, {"b": (3, 4)}]}
    assert attestation.deep_value_fingerprint(left) == (
        attestation.deep_value_fingerprint(right)
    )
    assert attestation.deep_value_fingerprint(left) != attestation.deep_value_fingerprint(
        {"a": [1, 2, {"b": (3, 5)}], "c": frozenset({"x", "y"})}
    )
    assert attestation.deep_value_fingerprint([1]) != (
        attestation.deep_value_fingerprint((1,))
    )
    assert attestation.deep_value_fingerprint(object()) == (
        attestation.UNSTABLE_VALUE_FINGERPRINT
    )


# ---------------------------------------------------------------------------
# Module route identity
# ---------------------------------------------------------------------------


def test_a_second_loaded_instance_of_the_certified_source_refuses(
    replica: types.ModuleType,
) -> None:
    expectations = _replica_expectations(replica)
    assert _attest(replica, expectations).conforms is True
    sys.modules[attestation.CALENDAR_MODULE_IMPORT_NAME] = production
    measured = _attest(replica, expectations)
    assert "DUPLICATE_CALENDAR_MODULE_INSTANCE" in measured.namespace_reasons


def test_a_module_that_is_not_an_exact_module_object_refuses() -> None:
    class Shim(types.ModuleType):
        pass

    shim = Shim(production.__name__)
    shim.__dict__.update(production.__dict__)
    assert "MODULE_IS_NOT_AN_EXACT_MODULE_OBJECT" in attestation._module_namespace_reasons(
        shim
    )


def test_a_module_not_bound_as_the_package_attribute_refuses() -> None:
    package = sys.modules["btc_predictor.research"]
    original = package.etf_publication_calendar
    try:
        package.etf_publication_calendar = types.ModuleType("decoy")
        assert "MODULE_NOT_BOUND_AS_THE_PACKAGE_ATTRIBUTE" in (
            attestation._module_namespace_reasons(production)
        )
    finally:
        package.etf_publication_calendar = original


def test_a_consumer_holding_its_own_owner_binding_refuses() -> None:
    consumer = types.ModuleType("etf_calendar_consumer_probe")

    def venue_session_status(*args: object, **kwargs: object) -> None:
        return None

    venue_session_status.__module__ = production.__name__
    consumer.venue_session_status = venue_session_status
    sys.modules[consumer.__name__] = consumer
    try:
        assert attestation.consumer_binding_divergence(production) == (
            "etf_calendar_consumer_probe:venue_session_status",
        )
        measured = _attest(production, _production_expectations())
        assert measured.conforms is False
        assert any("CONSUMER_BINDING_DIVERGENCE" in row for row in measured.reasons)
    finally:
        sys.modules.pop(consumer.__name__, None)
    assert attestation.consumer_binding_divergence(production) == ()


# ---------------------------------------------------------------------------
# Epoch result and exit-path rules
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "factory",
    [
        lambda: (value for value in (1, 2, 3)),
        lambda: map(str, (1, 2)),
        lambda: filter(None, (1, 2)),
        lambda: zip((1,), (2,)),
        lambda: iter([1, 2]),
    ],
)
def test_a_lazy_result_is_refused_before_admission(factory: object) -> None:
    expectations = _production_expectations()
    calls: list[str] = []
    with pytest.raises(
        attestation.RuntimeOwnerAttestationError,
        match="EPOCH_RESULT_IS_NOT_EAGERLY_EVALUATED",
    ) as excinfo:
        attestation.run_scientific_execution_epoch(
            _epoch(production, expectations),
            lambda module: factory(),
            lambda result: calls.append("admit"),
        )
    assert calls == []
    assert excinfo.value.evidence["result_admitted"] is False


@pytest.mark.parametrize("result", ["text", b"bytes", {"a": 1}, [1], (1,), {1}, 7])
def test_eager_results_are_admitted(result: object) -> None:
    outcome = attestation.run_scientific_execution_epoch(
        _epoch(production, _production_expectations()), lambda module: result
    )
    assert outcome.admitted is True
    assert outcome.result == result


def test_a_failing_epoch_sweeps_for_persistent_drift(
    replica: types.ModuleType,
) -> None:
    expectations = _replica_expectations(replica)

    def operation(module: types.ModuleType) -> str:
        module.__dict__["venue_session_status"] = _replacement(module)
        raise ValueError("scientific failure")

    with pytest.raises(
        attestation.RuntimeOwnerAttestationError,
        match="SCIENTIFIC_EXECUTION_EPOCH_DRIFT_DETECTED_ON_EXIT",
    ) as excinfo:
        attestation.run_scientific_execution_epoch(
            _epoch(replica, expectations), operation
        )
    assert excinfo.value.evidence["result_admitted"] is False
    assert excinfo.value.evidence["attestation_match"] is False


def test_a_clean_failing_epoch_propagates_its_own_error(
    replica: types.ModuleType,
) -> None:
    def operation(module: types.ModuleType) -> str:
        raise ValueError("scientific failure")

    with pytest.raises(ValueError, match="scientific failure"):
        attestation.run_scientific_execution_epoch(
            _epoch(replica, _replica_expectations(replica)), operation
        )
    assert getattr(attestation._EPOCH_STATE, "active", False) is False


def test_a_pre_attestation_that_misses_the_startup_baseline_refuses() -> None:
    expectations = _production_expectations()
    epoch = attestation.ScientificExecutionEpoch(
        epoch_id="epoch-baseline",
        module=production,
        expectations=expectations,
        source=CALENDAR_SOURCE_TEXT,
        calendar_authority_sha256="0" * 64,
        proof_architecture_sha256="0" * 64,
        decision_time="2026-09-19T00:00:00Z",
        baseline_digest="1" * 64,
    )
    with pytest.raises(
        attestation.RuntimeOwnerAttestationError,
        match="SCIENTIFIC_EXECUTION_NOT_AUTHORIZED",
    ):
        attestation.run_scientific_execution_epoch(epoch, lambda module: "result")


def test_a_source_digest_that_disagrees_with_the_parent_artifact_refuses() -> None:
    with pytest.raises(
        attestation.RuntimeOwnerAttestationError, match="MODULE_SOURCE_IDENTITY_MISMATCH"
    ):
        attestation.verify_module_source_identity(
            production, CALENDAR_SOURCE_TEXT, expected_source_sha256="0" * 64
        )
    assert attestation.verify_module_source_identity(
        production,
        CALENDAR_SOURCE_TEXT,
        expected_source_sha256=attestation.source_sha256(CALENDAR_SOURCE_TEXT),
    )["parent_artifact_digest_compared"] is True


def test_a_poisoned_owner_builtins_namespace_refuses(replica: types.ModuleType) -> None:
    expectations = _replica_expectations(replica)
    owner = replica.__dict__["_verify_schedule"]
    rebuilt = types.FunctionType(
        owner.__code__,
        replica.__dict__,
        owner.__name__,
        owner.__defaults__,
        owner.__closure__,
    )
    rebuilt.__qualname__ = owner.__qualname__
    rebuilt.__module__ = owner.__module__
    replica.__dict__["__builtins__"] = dict(vars(__import__("builtins")))
    poisoned = types.FunctionType(
        owner.__code__,
        replica.__dict__,
        owner.__name__,
        owner.__defaults__,
        owner.__closure__,
    )
    replica.__dict__["_verify_schedule"] = poisoned
    reasons = _reasons_for(replica, expectations, "_verify_schedule")
    assert "OWNER_BUILTINS_NAMESPACE_MISMATCH" in reasons
    assert rebuilt.__builtins__ is not None


# ---------------------------------------------------------------------------
# New frozen material
# ---------------------------------------------------------------------------


def test_transitive_execution_closure_rule_is_frozen() -> None:
    child = attestation.transitive_execution_closure_rule()
    assert child["closure_contract_version"] == (
        "CALENDAR_TRANSITIVE_EXECUTION_CLOSURE_V1"
    )
    assert child["derivation_is_a_hand_maintained_list"] is False
    assert child["recurses_into_nested_code_objects"] is True
    assert child["instruction_scan_deoptimizes_specialized_instructions"] is True
    assert child["closure_member_absent_from_the_frozen_expectation"] == "REFUSE"
    assert child["value_that_is_not_a_reviewable_literal"] == (
        "REFUSE_AS_CLOSURE_VALUE_NOT_STATICALLY_DERIVABLE"
    )
    assert child["project_owned_import_whole_module_function_attestation"] is True
    assert child["interpreter_provided_module_internals_attested"] is False
    assert child["seeded_by"] == [
        "EXACT_FROZEN_REPLAY_OWNERS",
        "DECLARED_CalendarEvidenceStore_ROOT_ANNOTATION_TYPE",
    ]


def test_epoch_rule_freezes_the_new_exit_path_and_result_rules() -> None:
    rule = attestation.scientific_execution_epoch_rule()
    assert rule["operation_may_persist_before_post_attestation"] is False
    assert rule["lazy_or_deferred_result_admitted"] is False
    assert rule["exception_path_sweeps_for_persistent_drift"] is True
    assert rule["duplicate_loaded_calendar_module_instance"] == "REFUSE"
    assert rule["pre_attestation_must_reproduce_the_startup_baseline"] is True
    assert rule["startup_ordering_rule"] == attestation.STARTUP_ORDERING_RULE


def test_transient_exclusion_is_stated_cause_neutrally() -> None:
    rule = attestation.pre_post_attestation_rule()
    assert rule["transient_mutate_and_restore_is_cause_neutral"] is True
    assert "BENIGN_CONCURRENT_PATCH_AND_RESTORE_BY_PROJECT_OWNED_CODE" in (
        rule["transient_mutate_and_restore_statement"]
    )
    assert rule["epoch_lock_serializes_epochs_against_non_epoch_threads"] is False
    assert rule["compared_surface"] == [
        "ELEVEN_FROZEN_REPLAY_OWNERS",
        "TRANSITIVE_EXECUTION_CLOSURE",
        "MODULE_ROUTE_AND_NAMESPACE_IDENTITY",
    ]


def test_production_result_records_the_closure_and_the_wrapper_blocker() -> None:
    result = attestation.verify_current_production_expected_result(CALENDAR_SOURCE_TEXT)
    assert result["runtime_effective_owner_bindings"] == (
        "ALL_ELEVEN_ATTEST_UNDER_THE_FROZEN_CONTRACT"
    )
    assert result["runtime_execution_closure_bindings"] == (
        "REFUSED_AT_THE_WRAPPER_INSTALLED_CalendarEvidenceStore_GUARDS"
    )
    assert result["execution_closure"]["functions"]
    assert set(result["certified_project_closure_module_sha256"]) == {
        "btc_predictor.features.flow",
        "btc_predictor.research.etf_calendar_semantics",
        "btc_predictor.research.trusted_acquisition",
        "btc_predictor.data",
    }


# ---------------------------------------------------------------------------
# End-to-end science demonstration on a conforming future implementation
# ---------------------------------------------------------------------------


@pytest.fixture()
def conforming_replica(replica: types.ModuleType) -> types.ModuleType:
    """A replica with the wrapper-installed dependency guards removed.

    The final calendar implementation must remove them, so this is the closest
    reachable stand-in for a conforming production module and gives the closure
    tier a clean negative control.
    """

    store = replica.__dict__["CalendarEvidenceStore"]
    for name in attestation.STORE_APIS:
        setattr(store, name, getattr(store, name).__wrapped__)
    return replica


def test_a_conforming_implementation_attests_cleanly_across_every_tier(
    conforming_replica: types.ModuleType,
) -> None:
    measured = _attest(
        conforming_replica,
        _replica_expectations(conforming_replica),
        _closure_expectations(conforming_replica),
    )
    assert measured.conforms is True
    assert measured.reasons == ()
    assert len(measured.owners) == 11
    assert len(measured.closure) == 50


def test_a_helper_substitution_that_changes_the_science_is_refused_end_to_end(
    conforming_replica: types.ModuleType,
) -> None:
    """Owner-only measurement admits the wrong answer; the closure refuses it."""

    from datetime import date, datetime, timedelta, timezone

    class _Store:
        def records(self, **kwargs: object) -> list[object]:
            return []

    def science(module: types.ModuleType) -> str:
        resolution = module.__dict__["venue_session_status"](
            "NYSE_ARCA",
            date(2025, 1, 4),
            datetime(2025, 1, 7, tzinfo=timezone.utc),
            _Store(),
        )
        return f"{resolution.venue_id}/{resolution.trade_date}/{resolution.state}"

    owners = _replica_expectations(conforming_replica)
    closure = _closure_expectations(conforming_replica)
    honest = attestation.run_scientific_execution_epoch(
        _epoch(conforming_replica, owners, closure=closure), science
    )
    assert honest.result == "NYSE_ARCA/2025-01-04/CLOSED"

    original = conforming_replica.__dict__["_parse_date"]
    conforming_replica.__dict__["_parse_date"] = (
        lambda value, field: original(value, field) + timedelta(days=1)
    )
    assert science(conforming_replica) == "NYSE_ARCA/2025-01-05/CLOSED"

    owner_only = attestation.run_scientific_execution_epoch(
        _epoch(conforming_replica, owners), science
    )
    assert owner_only.admitted is True
    assert owner_only.result == "NYSE_ARCA/2025-01-05/CLOSED"

    with pytest.raises(
        attestation.RuntimeOwnerAttestationError,
        match="SCIENTIFIC_EXECUTION_NOT_AUTHORIZED",
    ):
        attestation.run_scientific_execution_epoch(
            _epoch(conforming_replica, owners, closure=closure), science
        )


def test_class_method_descriptor_kinds_are_part_of_the_certified_expectation(
    conforming_replica: types.ModuleType,
) -> None:
    closure = _closure_expectations(conforming_replica)
    store = next(row for row in closure.classes if row.name == "CalendarEvidenceStore")
    kinds = {attribute: kind for attribute, kind, _ in store.certified_method_fingerprints}
    assert kinds["__init_subclass__"] == "CLASSMETHOD"
    assert kinds["put"] == "FUNCTION"
    original = conforming_replica.__dict__["CalendarEvidenceStore"].put
    conforming_replica.__dict__["CalendarEvidenceStore"].put = staticmethod(original)
    assert "CLOSURE_CLASS_CERTIFIED_METHOD_MISMATCH" in _closure_reasons(
        conforming_replica, "CalendarEvidenceStore"
    )
