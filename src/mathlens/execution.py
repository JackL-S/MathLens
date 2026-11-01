"""一次任务一个 spawn worker，JSON 管道通信和有界回收。"""

import logging
from multiprocessing import get_context
from multiprocessing.connection import Connection
from queue import Empty, Queue
from threading import Thread
from time import monotonic
from typing import overload

from .control import CancellationToken, ExecutionControl
from .enums import DiagnosticCode, MessageType, PreparationStatus, ProcessingStage, Status
from .schemas import (
    ApplicationResponse, ComputeResponse, ComputeTask, Diagnostic, ExecutionOptions,
    PreparationResponse, PrepareTask, ProgressEvent,
    RunTask, WorkerRequest, WorkerResult, WorkerTask,
)


def _failure(task, status: Status, code: DiagnosticCode, message: str) -> ApplicationResponse:
    diagnostics = (Diagnostic(code=code, message=message, severity=MessageType.ERROR,
                              stage=ProcessingStage.EXECUTION),)
    if isinstance(task, ComputeTask):
        return ComputeResponse(status=status, diagnostics=diagnostics)
    return PreparationResponse(status=PreparationStatus(status.value), diagnostics=diagnostics)


def _progress(control, message):
    if control is not None and control.on_progress is not None:
        try:
            control.on_progress(ProgressEvent(stage=ProcessingStage.EXECUTION, message=message))
        except Exception:
            logging.getLogger(__name__).exception("进度回调失败")


@overload
def execute(task: PrepareTask, *, options: ExecutionOptions | None = None,
            control: ExecutionControl | None = None) -> PreparationResponse: ...


@overload
def execute(task: ComputeTask, *, options: ExecutionOptions | None = None,
            control: ExecutionControl | None = None) -> ComputeResponse: ...


@overload
def execute(task: RunTask, *, options: ExecutionOptions | None = None,
            control: ExecutionControl | None = None) -> ApplicationResponse: ...


def execute(
    task: WorkerTask, *, options: ExecutionOptions | None = None,
    control: ExecutionControl | None = None,
) -> ApplicationResponse:
    from .codec import ContractDecodeError, decode_worker_result, encode_worker

    options = ExecutionOptions() if options is None else options
    if not isinstance(options, ExecutionOptions) or options.validate():
        return _failure(task, Status.ERROR, DiagnosticCode.INVALID_REQUEST, "执行选项无效")
    deadline = monotonic() + options.timeout_seconds
    cancelled = lambda: control is not None and control.cancellation is not None and control.cancellation.is_cancelled()
    if cancelled():
        return _failure(task, Status.CANCELLED, DiagnosticCode.CANCELLED, "任务已取消")
    try:
        request_json = encode_worker(WorkerRequest(task=task, options=options))
    except ContractDecodeError as exc:
        return _failure(task, Status.ERROR, DiagnosticCode.INVALID_REQUEST, str(exc))
    if len(request_json) > options.limits.max_input_bytes:
        return _failure(task, Status.ERROR, DiagnosticCode.RESOURCE_LIMIT_EXCEEDED, "任务输入超出字节限制")
    if monotonic() >= deadline:
        return _failure(task, Status.TIMEOUT, DiagnosticCode.DEADLINE_EXCEEDED, "任务超过总时限")

    context = get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=worker_main, args=(request_json, send))
    events: Queue[tuple[ApplicationResponse | None, Exception | None]] = Queue(maxsize=1)
    receiver = None
    result: ApplicationResponse | None = None
    cleaned = True

    def collect():
        try:
            payload = receive.recv_bytes(options.limits.max_output_bytes)
            response = decode_worker_result(payload).response
            expected = {
                "prepare": (PreparationResponse,), "compute": (ComputeResponse,),
                "run": (PreparationResponse, ComputeResponse),
            }[task.kind]
            if not isinstance(response, expected):
                raise ValueError("任务与响应类型不一致")
            events.put((response, None))
        except Exception as exc:
            events.put((None, exc))

    try:
        process.start()
        send.close()
        receiver = Thread(target=collect, daemon=True)
        receiver.start()
        _progress(control, "任务已启动")
        while result is None:
            if cancelled():
                result = _failure(task, Status.CANCELLED, DiagnosticCode.CANCELLED, "任务已取消")
                break
            remaining = deadline - monotonic()
            if remaining <= 0:
                result = _failure(task, Status.TIMEOUT, DiagnosticCode.DEADLINE_EXCEEDED, "任务超过总时限")
                break
            try:
                response, error = events.get(timeout=min(remaining, 0.02))
            except Empty:
                continue
            if error is not None:
                code = DiagnosticCode.RESOURCE_LIMIT_EXCEEDED if isinstance(error, OSError) and str(error) == "bad message length" else DiagnosticCode.WORKER_FAILED
                result = _failure(task, Status.ERROR, code, "worker 未能交付完整结果")
                break
            if monotonic() >= deadline:
                result = _failure(task, Status.TIMEOUT, DiagnosticCode.DEADLINE_EXCEEDED, "任务超过总时限")
            else:
                result = response
    except Exception:
        result = _failure(task, Status.ERROR, DiagnosticCode.WORKER_FAILED, "无法正常执行 worker")
    finally:
        cleanup_deadline = monotonic() + options.cleanup_timeout_seconds
        send.close()
        if process.pid is not None:
            process.join(timeout=min(0.05, max(0, cleanup_deadline - monotonic())))
            if process.is_alive():
                process.terminate()
                process.join(timeout=max(0, (cleanup_deadline - monotonic()) / 2))
            if process.is_alive():
                process.kill()
                process.join(timeout=max(0, cleanup_deadline - monotonic()))
            cleaned = not process.is_alive()
            if cleaned:
                process.close()
        receive.close()
        if receiver is not None:
            receiver.join(timeout=max(0, cleanup_deadline - monotonic()))
            cleaned = cleaned and not receiver.is_alive()
    if not cleaned:
        return _failure(task, Status.ERROR, DiagnosticCode.CLEANUP_FAILED, "未能确认 worker 和通道回收")
    _progress(control, "任务已结束")
    assert result is not None
    return result


def worker_main(request_json: bytes, result_conn: Connection) -> None:
    from .codec import ContractDecodeError, decode_worker_request, encode_worker

    task = None
    try:
        envelope = decode_worker_request(request_json)
        task = envelope.task
        from .pipeline import process_task
        response = process_task(task, envelope.options)
        payload = encode_worker(WorkerResult(response=response))
        if len(payload) > envelope.options.limits.max_output_bytes:
            response = _failure(task, Status.ERROR, DiagnosticCode.RESOURCE_LIMIT_EXCEEDED, "结果超出字节限制")
            payload = encode_worker(WorkerResult(response=response))
        result_conn.send_bytes(payload)
    except Exception as exc:
        try:
            code = DiagnosticCode(exc.code) if isinstance(exc, ContractDecodeError) else DiagnosticCode.WORKER_FAILED
            result_conn.send_bytes(encode_worker(WorkerResult(response=_failure(
                task, Status.ERROR, code, "worker 处理失败",
            ))))
        except Exception:
            pass
    finally:
        result_conn.close()
