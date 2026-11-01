"""父进程与 worker 共用的轻量预检；不依赖应用、执行器或数学后端。"""

from dataclasses import replace

from .enums import (
    DiagnosticCode, MessageType, MethodPolicy, PreparationStatus, ProcessingStage,
    Status, ValidationIssueKind,
)
from .schemas import (
    ComputeRequest, ComputeResponse, Diagnostic, DifferentiateSpec, ExecutionOptions,
    ImageInput, InputRequest, LatexInput, PreparationResponse, PreparedProblem,
    ResourceLimits, SimplifySpec, SolveSpec, ValidationIssue,
)
from .schemas.validation import invalid, matches_type, model_issues, text_issues


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


def check_request(
    request: ComputeRequest,
    *,
    options: ExecutionOptions | None = None,
) -> PreparationResponse | None:
    """检查请求并委托 Spec 校验自身参数，统一返回输入问题。

    父进程只做轻量检查；耗时解析和化简统一在 worker 内执行。
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

    feature_message = None
    if not isinstance(request.operation, SimplifySpec):
        feature_message = "当前计算后端仅支持显式化简"
    elif request.preferences.method is MethodPolicy.NUMERIC_ONLY:
        feature_message = "当前后端仅提供符号计算"
    elif any(symbol.latex is not None or any(
        getattr(symbol.assumptions, name) is not None
        for name in ("real", "integer", "positive", "nonnegative", "nonzero")
    ) for symbol in request.symbols):
        feature_message = "当前尚未接入符号假设或自定义符号映射"
    if feature_message:
        return PreparationResponse(status=PreparationStatus.UNSUPPORTED, diagnostics=(Diagnostic(
            code=DiagnosticCode.CAPABILITY_UNAVAILABLE, message=feature_message,
            severity=MessageType.ERROR, stage=ProcessingStage.PREPARE,
        ),))
    return None


def request_from_problem(problem: PreparedProblem) -> ComputeRequest:
    return ComputeRequest(
        input=problem.original_input, operation=problem.operation, symbols=problem.symbols,
        preferences=problem.preferences, schema_version=problem.schema_version,
    )


def compute_failure(failure: PreparationResponse) -> ComputeResponse:
    return ComputeResponse(
        status=Status(failure.status.value), input_requests=failure.input_requests,
        diagnostics=tuple(replace(item, field_paths=tuple(
            path.replace("/input", "/original_input", 1) for path in item.field_paths
        )) for item in failure.diagnostics),
    )


def check_problem(problem, options):
    if not matches_type(problem, PreparedProblem):
        return _validation_response(invalid("", "计算需要 PreparedProblem"))
    issues = text_issues(problem.latex, "/latex", "问题公式")
    if issues:
        return _validation_response(issues)
    return check_request(request_from_problem(problem), options=options)
