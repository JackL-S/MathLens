import os
from multiprocessing import active_children
from time import monotonic, sleep

import pytest

from mathlens import execution
from mathlens.application import run
from mathlens.control import ExecutionControl
from mathlens.enums import DiagnosticCode, PreparationStatus, Status
from mathlens.schemas import (
    ComputeRequest, ExecutionOptions, LatexInput, PrepareTask, ResourceLimits, SimplifySpec,
)


def _hung_worker(request_json, connection):
    # 保持写端打开，让接收线程阻塞在 recv_bytes；监督仍须可超时和取消。
    sleep(60)


def _crash(request_json, connection):
    os._exit(3)


def _oversized(request_json, connection):
    connection.send_bytes(b"x" * 20_000)


def _bad_json(request_json, connection):
    connection.send_bytes(b"not JSON")


class _Cancellation:
    def __init__(self, when):
        self.when = when

    def is_cancelled(self):
        return monotonic() >= self.when


def task():
    return PrepareTask(request=ComputeRequest(input=LatexInput(latex="x+x"), operation=SimplifySpec()))


def test_blocked_receive_times_out_and_next_request_works(monkeypatch):
    original = execution.worker_main
    monkeypatch.setattr(execution, "worker_main", _hung_worker)
    started = monotonic()
    response = execution.execute(task(), options=ExecutionOptions(
        timeout_seconds=0.8, cleanup_timeout_seconds=1,
    ))
    assert response.status is PreparationStatus.TIMEOUT
    assert response.diagnostics[0].code is DiagnosticCode.DEADLINE_EXCEEDED
    assert monotonic() - started < 4
    assert not active_children()
    monkeypatch.setattr(execution, "worker_main", original)
    response = run(task().request)
    assert response.status is Status.SUCCESS


@pytest.mark.parametrize("target,expected", [
    (_crash, DiagnosticCode.WORKER_FAILED),
    (_oversized, DiagnosticCode.RESOURCE_LIMIT_EXCEEDED),
    (_bad_json, DiagnosticCode.WORKER_FAILED),
])
def test_worker_failures_return_structured_errors(monkeypatch, target, expected):
    monkeypatch.setattr(execution, "worker_main", target)
    response = execution.execute(task(), options=ExecutionOptions(
        timeout_seconds=5, limits=ResourceLimits(max_output_bytes=1000),
    ))
    assert response.status is PreparationStatus.ERROR
    assert response.diagnostics[0].code is expected


def test_cancellation_interrupts_blocked_receive(monkeypatch):
    monkeypatch.setattr(execution, "worker_main", _hung_worker)
    response = execution.execute(task(), control=ExecutionControl(
        cancellation=_Cancellation(monotonic() + 0.4),
    ))
    assert response.status is PreparationStatus.CANCELLED
    assert response.diagnostics[0].code is DiagnosticCode.CANCELLED


def test_cancelled_before_start_does_not_launch_worker(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("取消后不应启动进程")
    monkeypatch.setattr(execution, "get_context", forbidden)
    response = execution.execute(task(), control=ExecutionControl(cancellation=_Cancellation(0)))
    assert response.status is PreparationStatus.CANCELLED
