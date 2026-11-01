"""各入口共用的应用接口；这里只声明契约。"""
from .enums import DiagnosticCode, PreparationStatus, MessageType, ProcessingStage
from .execution import ExecutionControl
from .schemas import (
    ApplicationResponse, Capabilities, ComputeRequest, ComputeResponse,
    ExecutionOptions, PreparationResponse, PreparedProblem, Diagnostic, SCHEMA_VERSION, ImageInput, InputRequest,
    LatexInput, OperationSpec,
)


def prepare(
    request: ComputeRequest,
    *,
    options: ExecutionOptions | None = None,
    control: ExecutionControl | None = None,
) -> PreparationResponse:
    """识别、预览并确认问题；歧义返回 input_requests，不擅自计算。

    成功返回 ready 和 PreparedProblem。耗时解析及 OCR 同样受执行控制。
    输入错误通过响应表达。
    """
    # 判断request是否是ComputeRequest
    if not isinstance(request, ComputeRequest):
        return PreparationResponse(
            status=PreparationStatus.ERROR,
            diagnostics=(
                Diagnostic(
                    code=DiagnosticCode.INVALID_REQUEST,
                    message="请求必须是 ComputeRequest",
                    severity=MessageType.ERROR,
                    stage=ProcessingStage.PREPARE,
                    field_paths=("",),
                ),
            ),
        )
    # 判断schema_version
    if type(request.schema_version) is not int or request.schema_version != SCHEMA_VERSION:
        return PreparationResponse(
            status=PreparationStatus.ERROR,
            diagnostics=(
                Diagnostic(
                    code=DiagnosticCode.SCHEMA_VERSION_MISMATCH,
                    message="版本类型或值不正确",
                    severity=MessageType.ERROR,
                    stage=ProcessingStage.PREPARE,
                    field_paths=("/schema_version",),
                ),
            )
        )
    # input合法性检查
    if not isinstance(request.input, (ImageInput, LatexInput)):
        return PreparationResponse(
            status=PreparationStatus.ERROR,
            diagnostics=(
                Diagnostic(
                    code=DiagnosticCode.INVALID_REQUEST,
                    message="输入必须是 LatexInput 或 ImageInput",
                    severity=MessageType.ERROR,
                    stage=ProcessingStage.PREPARE,
                    field_paths=("/input",),
                ),
            )
        )

    # TODO:未来实现ImageInput
    if isinstance(request.input, ImageInput):
        return PreparationResponse(
            status=PreparationStatus.UNSUPPORTED,
            diagnostics=(
                Diagnostic(
                    code=DiagnosticCode.CAPABILITY_UNAVAILABLE,
                    message="当前尚未支持图片输入",
                    severity=MessageType.ERROR,
                    stage=ProcessingStage.PREPARE,
                    field_paths=("/input",),
                ),
            ),
        )
    # latex输入检查
    if not isinstance(request.input.latex, str):
        return PreparationResponse(
            status=PreparationStatus.ERROR,
            diagnostics=(
                Diagnostic(
                    code=DiagnosticCode.INVALID_REQUEST,
                    message="LaTeX 公式必须是字符串",
                    severity=MessageType.ERROR,
                    stage=ProcessingStage.PREPARE,
                    field_paths=("/input/latex",),
                ),
            ),
        )

    if not request.input.latex.strip():
        return PreparationResponse(
            status=PreparationStatus.ERROR,
            diagnostics=(
                Diagnostic(
                    code=DiagnosticCode.INVALID_LATEX,
                    message="公式不能为空",
                    severity=MessageType.ERROR,
                    stage=ProcessingStage.PREPARE,
                    field_paths=("/input/latex",),
                ),
            ),
        )
    # 运算检查
    if request.operation is None:
        return PreparationResponse(
            status=PreparationStatus.NEEDS_INPUT,
            input_requests=(
                InputRequest(
                    code=DiagnosticCode.MISSING_OPERATION,
                    message="请选择要执行的运算",
                    field_path="/operation",
                ),
            ),
        )
    if not isinstance(request.operation, OperationSpec):
        return PreparationResponse(
            status=PreparationStatus.ERROR,
            diagnostics=(
                Diagnostic(
                    code=DiagnosticCode.INVALID_REQUEST,
                    message="运算必须使用对应的运算规格模型",
                    severity=MessageType.ERROR,
                    stage=ProcessingStage.PREPARE,
                    field_paths=("/operation",),
                ),
            ),
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
