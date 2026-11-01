"""公开应用入口：轻量预检后提交受执行预算控制的任务。"""

from .control import ExecutionControl
from .enums import MethodPolicy, Operation
from .preflight import check_problem, check_request, compute_failure
from .schemas import (
    ApplicationResponse, Capabilities, ComputeRequest, ComputeResponse, ComputeTask,
    ExecutionOptions, OperationCapability, PreparationResponse, PreparedProblem,
    PrepareTask, RunTask,
)


def prepare(
    request: ComputeRequest, *, options: ExecutionOptions | None = None,
    control: ExecutionControl | None = None,
) -> PreparationResponse:
    """在有预算的 worker 内清理并解析公式，生成可计算快照。"""
    failure = check_request(request, options=options)
    if failure is not None:
        return failure
    from .execution import execute
    return execute(PrepareTask(request=request), options=options, control=control)


def compute(
    problem: PreparedProblem, *, options: ExecutionOptions | None = None,
    control: ExecutionControl | None = None,
) -> ComputeResponse:
    """重新检查快照，在独立 worker 内化简并保留原式条件。"""
    failure = check_problem(problem, options)
    if failure is not None:
        return compute_failure(failure)
    from .execution import execute
    return execute(ComputeTask(problem=problem), options=options, control=control)


def run(
    request: ComputeRequest, *, options: ExecutionOptions | None = None,
    control: ExecutionControl | None = None,
) -> ApplicationResponse:
    """一个 worker 内准备并计算，复用解析结果和总预算。"""
    failure = check_request(request, options=options)
    if failure is not None:
        return failure
    from .execution import execute
    return execute(RunTask(request=request), options=options, control=control)


def get_capabilities() -> Capabilities:
    return Capabilities(
        operations=(OperationCapability(operation=Operation.SIMPLIFY,
                    methods=(MethodPolicy.SYMBOLIC_FIRST, MethodPolicy.SYMBOLIC_ONLY)),),
        input_kinds=("latex",), supports_cancellation=True,
    )
