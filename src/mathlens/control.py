"""与执行后端无关的运行时控制，不进入公开 JSON。"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from .schemas.tasks import ProgressEvent


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
