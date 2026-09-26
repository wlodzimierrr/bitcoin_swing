"""TEST / REVIEW HARNESS ONLY — raw, unverified worker execution.

This module exists for exactly one reason: ``POSTP1-002V2A-PAD4-R2`` proved a
bypass, and a correction that cannot reproduce the old failure as a *control*
has proved nothing.  It deliberately reproduces the reviewed ``PAD4-R2`` raw
capability — spawn a worker process with **no** trusted-controller bootstrap
pre-verification whatsoever — so the mandatory R3 regressions can show, first,
that the fabrication genuinely succeeds at the raw process layer, and second,
that nothing it produces can enter R3 scientific admission or obtain
affirmative R3 scientific authority evidence.

It is **not** production scientific-controller code:

* it lives under ``btc_predictor/tests``, outside the production research
  package and outside the certified worker source universe;
* its outcome type is ``RawWorkerProcessOutcome``, a materially distinct
  concept that no production admission or evidence surface accepts, because
  after ``POSTP1-001V2A-PAD4-R3`` there is no production admission or evidence
  surface that accepts anything at all — every step is closure-owned by
  ``run_isolated_scientific_request``;
* the only evidence it can produce is stamped
  ``NON_AUTHORITATIVE_RAW_EXECUTION`` and ``admitted = False``, unambiguously
  and unconditionally; and
* it cannot emit the affirmative authority marker.  The mechanical API-closure
  audit reads this file and refuses if that marker ever appears here.

A leading underscore was the ``PAD4-R2`` boundary and it was not a boundary.
The boundary here is that the production authority path owns its capability in
a closure and offers no composable entry point, so this harness has nothing to
compose with.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from btc_predictor.research import etf_calendar_isolated_scientific_worker_r3 as r3
from etf_calendar_worker import protocol_r2 as protocol


RAW_HARNESS_VERSION = "ETF_CALENDAR_RAW_UNVERIFIED_WORKER_REVIEW_HARNESS_V1_R3"

#: The reason a raw execution can never be scientific authority, restated where
#: the raw capability actually lives.
RAW_EXECUTION_IS_NOT_AUTHORITY = (
    "A_RAW_EXECUTION_WAS_NOT_PERFORMED_BY_THE_CLOSED_AUTHORITATIVE_CONTROLLER"
)


@dataclass(frozen=True)
class RawWorkerProcessOutcome:
    """A raw, unverified worker process observation.

    Materially distinct from anything the production controller produces.  No
    production function consumes it, and it carries an explicit, unconditional
    statement that it is not scientific authority.  A caller may construct it
    freely — that is the point of the control — and constructing it must remain
    completely useless for obtaining scientific authority.
    """

    exit_status: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes
    request_digest: str
    bootstrap_pre_verification: Mapping[str, Any] | None = None

    @property
    def clean_termination(self) -> bool:
        return self.exit_status == 0 and not self.timed_out

    @property
    def scientific_authority(self) -> str:
        return r3.NON_AUTHORITATIVE_SCIENTIFIC_AUTHORITY

    @property
    def scientifically_admissible(self) -> bool:
        return False


def raw_unverified_worker_execution(
    request: Mapping[str, Any],
    launch: r3.WorkerLaunch,
    *,
    pycache_namespace: Path | None = None,
    bootstrap_pre_verification: Mapping[str, Any] | None = None,
) -> RawWorkerProcessOutcome:
    """Spawn a worker with no trusted-controller pre-verification at all.

    This is the reviewed ``PAD4-R2`` ``_spawn_unverified_worker_process``
    capability, moved out of production code.  It performs no bootstrap
    binding, so a drifted bootstrap tree really does execute and really can
    fabricate a successful response — which is exactly the control the
    mandatory R3 bypass regressions need.
    """

    r3.authorize_worker_launch_mechanism(launch.mechanism)
    payload = protocol.canonical_json_bytes(request)
    digest = protocol.digest_bytes(payload)
    owned = pycache_namespace is None
    namespace = (
        r3.allocate_worker_pycache_namespace(launch.pycache_namespace_root)
        if owned
        else Path(pycache_namespace).resolve()
    )
    try:
        completed = subprocess.run(
            list(launch.argv_for(namespace)),
            input=payload,
            capture_output=True,
            cwd=str(launch.cwd),
            env=dict(launch.environment),
            timeout=launch.timeout_seconds,
            close_fds=True,
        )
    except subprocess.TimeoutExpired as expired:
        return RawWorkerProcessOutcome(
            exit_status=None,
            timed_out=True,
            stdout=expired.stdout or b"",
            stderr=expired.stderr or b"",
            request_digest=digest,
            bootstrap_pre_verification=bootstrap_pre_verification,
        )
    finally:
        if owned:
            shutil.rmtree(namespace, ignore_errors=True)
    return RawWorkerProcessOutcome(
        exit_status=completed.returncode,
        timed_out=False,
        stdout=completed.stdout,
        stderr=completed.stderr,
        request_digest=digest,
        bootstrap_pre_verification=bootstrap_pre_verification,
    )


def raw_execution_diagnostic(outcome: RawWorkerProcessOutcome) -> dict[str, Any]:
    """Diagnostic — never authority — for one raw, unverified execution.

    Every field that could be mistaken for scientific authority is stamped
    negatively and unconditionally.  The caller-supplied
    ``bootstrap_pre_verification`` mapping is reported as *what the caller
    supplied*, explicitly labelled diagnostic, and it never changes any verdict:
    a fabricated PASS mapping produces exactly the same refusal as ``None``.
    """

    if not isinstance(outcome, RawWorkerProcessOutcome):
        raise TypeError(
            "the raw diagnostic accepts only a RawWorkerProcessOutcome; "
            "authoritative scientific material is produced by "
            "run_isolated_scientific_request and by nothing else"
        )
    return {
        "scientific_authority": r3.NON_AUTHORITATIVE_SCIENTIFIC_AUTHORITY,
        "diagnostic_version": RAW_HARNESS_VERSION,
        "admitted": False,
        "reason": RAW_EXECUTION_IS_NOT_AUTHORITY,
        "authoritative_execution_is_closed_end_to_end": False,
        "bootstrap_pre_execution_source_binding": {
            "performed_by_a_trusted_controller": False,
            "performed_by_this_execution": False,
            "caller_supplied_mapping_is_diagnostic_not_authority": True,
            "caller_supplied_mapping_present": (
                outcome.bootstrap_pre_verification is not None
            ),
        },
        "process_exit_status": outcome.exit_status,
        "process_timed_out": outcome.timed_out,
        "request_digest": outcome.request_digest,
        "result": None,
        "result_digest": None,
    }
