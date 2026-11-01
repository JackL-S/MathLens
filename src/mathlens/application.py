"""应用入口：组织输入检查、Spec 校验和后续准备流程。"""

from .enums import (
    DiagnosticCode, MessageType, PreparationStatus, ProcessingStage,
    ValidationIssueKind,
)
from .control import ExecutionControl
from .schemas import (
    ApplicationResponse, Capabilities, ComputeRequest,
    ComputeResponse, Diagnostic, ExecutionOptions, ImageInput, InputRequest,
    DifferentiateSpec, LatexInput, PreparationResponse, PreparedProblem,
    ResourceLimits, SolveSpec, ValidationIssue,
)
from .schemas.validation import invalid, matches_type, model_issues


def _validation_response(
    issues: tuple[ValidationIssue, ...],
    *, stage: ProcessingStage = ProcessingStage.PREPARE,
) -> PreparationResponse:
    """转换校验问题；无效参数优先报错，同时保留可操作的补充项。"""
    diagnostics = tuple(
        Diagnostic(
            code=issue.code, message=issue.message,
            severity=MessageType.ERROR, stage=stage,
            field_paths=(issue.field_path,),
        )
        for issue in issues if issue.kind is ValidationIssueKind.INVALID
    )
    input_requests = tuple(
        InputRequest(
            code=issue.code, message=issue.message, field_path=issue.field_path,
        )
        for issue in issues if issue.kind in (
            ValidationIssueKind.MISSING, ValidationIssueKind.CONFLICT,
        )
    )
    return PreparationResponse(
        status=PreparationStatus.ERROR if diagnostics else PreparationStatus.NEEDS_INPUT,
        diagnostics=diagnostics, input_requests=input_requests,
    )


def _request_limit_issues(
    request: ComputeRequest, limits: ResourceLimits,
) -> tuple[ValidationIssue, ...]:
    """只消费已通过结构校验的请求和限制；不解析公式、不执行计算。"""
    issues = ()
    if isinstance(request.input, LatexInput):
        try:
            size = len(request.input.latex.encode("utf-8"))
        except UnicodeEncodeError:
            issues += invalid("/input/latex", "公式含有非法 Unicode 字符", DiagnosticCode.INVALID_LATEX)
        else:
            if size > limits.max_input_bytes:
                issues += invalid(
                    "/input/latex", "公式超过输入字节限制", DiagnosticCode.RESOURCE_LIMIT_EXCEEDED,
                )
    if request.preferences.significant_digits > limits.max_significant_digits:
        issues += invalid(
            "/preferences/significant_digits", "展示精度超过限制", DiagnosticCode.RESOURCE_LIMIT_EXCEEDED,
        )
    operation = request.operation
    if isinstance(operation, DifferentiateSpec):
        for index, target in enumerate(operation.targets):
            if target.order > limits.max_derivative_order:
                issues += invalid(
                    f"/operation/targets/{index}/order", "求导阶数超过限制",
                    DiagnosticCode.RESOURCE_LIMIT_EXCEEDED,
                )
    if isinstance(operation, SolveSpec) and operation.numeric is not None:
        if operation.numeric.significant_digits > limits.max_significant_digits:
            issues += invalid(
                "/operation/numeric/significant_digits", "求解精度超过限制",
                DiagnosticCode.RESOURCE_LIMIT_EXCEEDED,
            )
    return issues


def prepare(
    request: ComputeRequest,
    *,
    options: ExecutionOptions | None = None,
    control: ExecutionControl | None = None,
) -> PreparationResponse:
    """检查请求并委托 Spec 校验自身参数，统一返回输入问题。

    构造 Spec 不执行校验，不因输入问题抛异常。参数检查通过后还需解析、
    预览和语义检查；尚未接入时明确返回能力不可用，不提前报告 ready。
    """
    if not matches_type(request, ComputeRequest):
        return _validation_response((ValidationIssue(
            kind=ValidationIssueKind.INVALID, code=DiagnosticCode.INVALID_REQUEST,
            message="请求必须是 ComputeRequest", field_path="",
        ),))
    issues = request.validate()
    if issues:
        return _validation_response(issues)

    effective_options = ExecutionOptions() if options is None else options
    option_issues = model_issues(
        effective_options, ExecutionOptions, "", lambda value: value.validate(),
    )
    if option_issues:
        return _validation_response(option_issues, stage=ProcessingStage.EXECUTION)
    limit_issues = _request_limit_issues(request, effective_options.limits)
    if limit_issues:
        return _validation_response(limit_issues)
    if isinstance(request.input, ImageInput):
        return PreparationResponse(
            status=PreparationStatus.UNSUPPORTED,
            diagnostics=(Diagnostic(
                code=DiagnosticCode.CAPABILITY_UNAVAILABLE,
                message="当前尚未支持图片输入", severity=MessageType.ERROR,
                stage=ProcessingStage.PREPARE, field_paths=("/input",),
            ),),
        )

    return PreparationResponse(
        status=PreparationStatus.UNSUPPORTED,
        diagnostics=(Diagnostic(
            code=DiagnosticCode.CAPABILITY_UNAVAILABLE,
            message="参数检查已通过，尚未接入公式解析与问题构建",
            severity=MessageType.ERROR, stage=ProcessingStage.PREPARE,
        ),),
    )


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
