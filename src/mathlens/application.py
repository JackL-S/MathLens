"""各入口共用的应用接口；这里只声明契约。"""

from .execution import ExecutionControl
from .schemas import (
    ApplicationResponse, Capabilities, ComputeRequest, ComputeResponse,
    ExecutionOptions, PreparationResponse, PreparedProblem,
)


def prepare(
    request: ComputeRequest,
    *,
    options: ExecutionOptions | None = None,
    control: ExecutionControl | None = None,
) -> PreparationResponse:
    """识别、预览并确认问题；歧义返回 input_requests，不擅自计算。

    成功返回 ready 和 PreparedProblem。耗时解析及 OCR 同样受执行控制。
    输入错误通过响应表达；当前接口未实现，抛出 NotImplementedError。
    """
    raise NotImplementedError


def compute(
    problem: PreparedProblem,
    *,
    options: ExecutionOptions | None = None,
    control: ExecutionControl | None = None,
) -> ComputeResponse:
    """计算已确认快照；检查快照约束，保留原式条件，不重新猜测意图。

    步骤不可用不影响已完成答案；取消和超时必须完成有界资源回收。
    数学内容修改须重新 prepare，不能把 PreparedProblem 当免校验令牌。
    """
    raise NotImplementedError


def run(
    request: ComputeRequest,
    *,
    options: ExecutionOptions | None = None,
    control: ExecutionControl | None = None,
) -> ApplicationResponse:
    """准备并计算；准备未就绪时返回 preparation，否则返回 computation。

    全流程共用一个预算，不能为每个阶段重新分配完整时限。
    """
    raise NotImplementedError


def get_capabilities() -> Capabilities:
    """查询实际启用能力；类型定义和枚举存在不代表功能可用。"""
    raise NotImplementedError
