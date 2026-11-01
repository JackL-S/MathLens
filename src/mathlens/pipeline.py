"""worker 内的化简切片；本模块加载数学依赖，不由应用入口提前导入。"""

from dataclasses import replace
from time import monotonic

from .enums import (
    DiagnosticCode, MessageType, PreparationStatus, ProcessingStage,
    ResultKind, Status, StepsStatus,
)
from .preflight import check_problem, check_request, compute_failure, request_from_problem
from .parsing import MathInputError
from .parsing.latex import ParsedExpression, parse_expression
from .parsing.normalize import normalize_latex
from .schemas import (
    ApplicationResponse, ComputationAttempt, ComputeRequest, ComputeResponse,
    Diagnostic, ExpressionValue, LatexInput, MathCondition, PreparationResponse,
    PreparedProblem, SimplifySpec, StepsResult, ComputeTask, ExecutionOptions,
    PrepareTask, WorkerTask,
)
from .solving.serialization import expression_to_display
from .solving.symbolic import simplify_expression


def prepare_core(request: ComputeRequest) -> tuple[PreparationResponse, ParsedExpression | None]:
    assert isinstance(request.input, LatexInput) and isinstance(request.operation, SimplifySpec)
    try:
        normalized, changes = normalize_latex(request.input.latex)
        parsed = parse_expression(normalized)
    except MathInputError as exc:
        return PreparationResponse(
            status=exc.status,
            diagnostics=(Diagnostic(
                code=exc.code, message=str(exc), severity=MessageType.ERROR,
                stage=ProcessingStage.PARSE, field_paths=("/input/latex",),
            ),),
        ), None
    problem = PreparedProblem(
        original_input=request.input, latex=normalized, operation=request.operation,
        symbols=request.symbols, preferences=request.preferences, changes=changes,
    )
    return PreparationResponse(
        status=PreparationStatus.READY, problem=problem,
        preview=expression_to_display(parsed.expression),
    ), parsed


def compute_parsed(problem: PreparedProblem, parsed: ParsedExpression) -> ComputeResponse:
    started = monotonic()
    try:
        result = simplify_expression(parsed.expression)
        display = expression_to_display(result)
        conditions = tuple(MathCondition(expression=expression_to_display(item)) for item in parsed.conditions)
    except Exception:
        return ComputeResponse(
            status=Status.ERROR, problem=problem,
            diagnostics=(Diagnostic(
                code=DiagnosticCode.COMPUTATION_FAILED, message="符号化简失败",
                severity=MessageType.ERROR, stage=ProcessingStage.COMPUTE,
            ),),
        )
    steps = StepsResult()
    if problem.preferences.include_steps:
        steps = StepsResult(status=StepsStatus.UNAVAILABLE, diagnostics=(Diagnostic(
            code=DiagnosticCode.STEPS_UNAVAILABLE, message="当前化简未提供推导步骤",
            severity=MessageType.INFO, stage=ProcessingStage.STEPS,
        ),))
    diagnostics = ()
    if problem.preferences.include_approximation:
        diagnostics = (Diagnostic(
            code=DiagnosticCode.APPROXIMATION_UNAVAILABLE, message="当前切片仅返回精确结果",
            severity=MessageType.INFO, stage=ProcessingStage.COMPUTE,
        ),)
    return ComputeResponse(
        status=Status.SUCCESS, problem=problem, result_kind=ResultKind.EXACT,
        value=ExpressionValue(expression=display),
        latex=display.latex + (
            r"\quad\text{for }" + r",\;".join(item.expression.latex for item in conditions)
            if conditions else ""
        ),
        conditions=conditions, steps=steps, diagnostics=diagnostics,
        attempts=(ComputationAttempt(method="sympy.simplify", status=Status.SUCCESS,
                                     elapsed_seconds=monotonic() - started),),
    )


def run_core(request: ComputeRequest) -> ApplicationResponse:
    prepared, parsed = prepare_core(request)
    if prepared.status is not PreparationStatus.READY:
        return prepared
    assert prepared.problem is not None and parsed is not None
    return compute_parsed(prepared.problem, parsed)


def compute_core(problem: PreparedProblem, request: ComputeRequest) -> ComputeResponse:
    prepared, parsed = prepare_core(request)
    if prepared.status is not PreparationStatus.READY:
        return ComputeResponse(
            status=Status(prepared.status.value), problem=problem,
            diagnostics=tuple(replace(item, field_paths=tuple(
                path.replace("/input", "/original_input", 1) for path in item.field_paths
            )) for item in prepared.diagnostics), input_requests=prepared.input_requests,
        )
    assert prepared.problem is not None and parsed is not None
    if problem.latex != prepared.problem.latex or problem.changes != prepared.problem.changes:
        return ComputeResponse(status=Status.ERROR, diagnostics=(Diagnostic(
            code=DiagnosticCode.INVALID_REQUEST, message="问题快照与原始输入不一致，请重新准备",
            severity=MessageType.ERROR, stage=ProcessingStage.PREPARE,
            field_paths=("/latex", "/changes"),
        ),))
    return compute_parsed(prepared.problem, parsed)


def process_task(task: WorkerTask, options: ExecutionOptions) -> ApplicationResponse:
    """worker 唯一分发点；不调用公共入口，避免递归创建进程。"""
    if isinstance(task, ComputeTask):
        failure = check_problem(task.problem, options)
        if failure is not None:
            return compute_failure(failure)
        return compute_core(task.problem, request_from_problem(task.problem))
    failure = check_request(task.request, options=options)
    if failure is not None:
        return failure
    if isinstance(task, PrepareTask):
        return prepare_core(task.request)[0]
    return run_core(task.request)
