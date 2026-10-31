"""执行、取消及进度契约；进程机制和数学算法尚未实现。"""

from collections.abc import Callable
from dataclasses import dataclass
from multiprocessing.connection import Connection
from typing import Protocol

from .schemas import ExecutionOptions, ProgressEvent, WorkerResponse, WorkerTask


class CancellationToken(Protocol):
    """仅在运行时使用；不进入数学请求或 JSON。"""

    def is_cancelled(self) -> bool:
        """是否收到取消请求；不代表后台资源已回收。"""
        ...


@dataclass(frozen=True, kw_only=True)
class ExecutionControl:
    """调用端控制对象；回调在监督端触发，不作为 worker 启动参数。"""

    cancellation: CancellationToken | None = None
    on_progress: Callable[[ProgressEvent], None] | None = None


def execute(
    task: WorkerTask,
    *,
    options: ExecutionOptions | None = None,
    control: ExecutionControl | None = None,
) -> WorkerResponse:
    """在隔离 worker 中执行任务，覆盖识别、准备和计算等耗时阶段。

    按总时限监督启动到结果接收；清理最多另用 cleanup_timeout_seconds。
    采用 JSON bytes 通信，限时限长接收；返回前确认回收，否则报 error。
    响应 kind 必须与 task kind 匹配。不能在父进程直接执行耗时解析。
    """
    raise NotImplementedError


def worker_main(request_json: bytes, result_conn: Connection) -> None:
    """读取 WorkerRequest，发送一次 WorkerResult 后关闭单向发送端。

    使用 send_bytes 传 UTF-8 JSON，不传第三方对象；数学模块延迟导入。
    进度不复用最终结果管道，具体事件传输机制由执行后端另行实现。
    """
    raise NotImplementedError
