"""后台任务接口；任务状态与数学处理状态分别表达。"""

from .schemas import (
    CancelResponse, ExecutionOptions, JobHandle, JobSnapshot, WorkerTask,
)


def submit(
    task: WorkerTask,
    *,
    options: ExecutionOptions | None = None,
) -> JobHandle:
    """提交任务并持有相关输入资源；预算从提交起包含排队时间。"""
    raise NotImplementedError


def get_job(job_id: str) -> JobSnapshot:
    """读取当前快照；未知或已过期标识抛 KeyError，由入口映射诊断。"""
    raise NotImplementedError


def cancel_job(job_id: str) -> CancelResponse:
    """请求取消，accepted 不代表回收完成；终态任务不重新转换状态。

    未知或已过期标识抛 KeyError。重复取消非终态任务可返回 accepted。
    """
    raise NotImplementedError
