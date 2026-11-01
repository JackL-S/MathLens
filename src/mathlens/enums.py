"""公开契约枚举；枚举存在不代表后端已支持该能力。"""

from enum import StrEnum, unique


class Operation(StrEnum):
    EVALUATE = "evaluate"
    SIMPLIFY = "simplify"
    DIFFERENTIATE = "differentiate"
    INTEGRATE = "integrate"
    SOLVE_EQUATION = "solve_equation"
    LIMIT = "limit"


class Domain(StrEnum):
    REAL = "real"
    COMPLEX = "complex"
    INTEGER = "integer"


class Status(StrEnum):
    SUCCESS = "success"
    NEEDS_INPUT = "needs_input"
    UNSUPPORTED = "unsupported"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class PreparationStatus(StrEnum):
    READY = "ready"
    NEEDS_INPUT = "needs_input"
    UNSUPPORTED = "unsupported"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ResultKind(StrEnum):
    EXACT = "exact"
    APPROXIMATE = "approximate"
    MIXED = "mixed"
    UNEVALUATED = "unevaluated"
    NONE = "none"


class Completeness(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class MessageType(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ProcessingStage(StrEnum):
    INPUT = "input"
    RECOGNIZE = "recognize"
    PREPARE = "prepare"
    PARSE = "parse"
    COMPUTE = "compute"
    VALIDATE = "validate"
    STEPS = "steps"
    SERIALIZE = "serialize"
    EXECUTION = "execution"


class MethodPolicy(StrEnum):
    SYMBOLIC_ONLY = "symbolic_only"
    SYMBOLIC_FIRST = "symbolic_first"
    NUMERIC_ONLY = "numeric_only"


class LimitDirection(StrEnum):
    BOTH = "both"
    LEFT = "left"
    RIGHT = "right"


class StepsStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    AVAILABLE = "available"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class ValidationIssueKind(StrEnum):
    """输入校验问题的性质，不等同于整个准备流程的状态。"""

    INVALID = "invalid"
    MISSING = "missing"
    CONFLICT = "conflict"


@unique
class DiagnosticCode(StrEnum):
    """全流程稳定原因码，与处理状态和消息级别分别表达。

    按问题性质分组，不反映某个开发阶段是否完成。内部使用这些成员，
    外部未知代码保留为字符串；完整含义见 docs/diagnostics.md。
    """

    # 请求结构、协议与资源限制。
    INVALID_REQUEST = "invalid_request"
    INVALID_JSON = "invalid_json"
    SCHEMA_VERSION_MISMATCH = "schema_version_mismatch"
    PROTOCOL_VERSION_MISMATCH = "protocol_version_mismatch"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"

    # 图片资源与识别。图片无效不等于公式识别失败。
    MEDIA_NOT_FOUND = "media_not_found"
    INVALID_IMAGE = "invalid_image"
    INVALID_IMAGE_REGION = "invalid_image_region"
    RECOGNITION_FAILED = "recognition_failed"
    OCR_CONFIRMATION_REQUIRED = "ocr_confirmation_required"

    # 公式语法、解释歧义与解析器故障。
    INVALID_LATEX = "invalid_latex"
    AMBIGUOUS_EXPRESSION = "ambiguous_expression"
    PARSER_FAILED = "parser_failed"

    # 数学参数补充与冲突。
    MISSING_FIELD = "missing_field"
    MISSING_OPERATION = "missing_operation"
    MISSING_VARIABLE = "missing_variable"
    MISSING_BOUND = "missing_bound"
    AMBIGUOUS_OPERATION = "ambiguous_operation"
    CONFLICTING_ARGUMENTS = "conflicting_arguments"

    # 数学方法和结果；发散可以是成功判定，步骤不可用不影响答案。
    SYMBOLIC_NOT_COMPLETED = "symbolic_not_completed"
    NUMERIC_NOT_CONVERGED = "numeric_not_converged"
    COMPUTATION_FAILED = "computation_failed"
    DIVERGENCE_DETECTED = "divergence_detected"
    RESULT_VALIDATION_FAILED = "result_validation_failed"
    STEPS_UNAVAILABLE = "steps_unavailable"
    APPROXIMATION_UNAVAILABLE = "approximation_unavailable"

    # 执行、任务和输出。
    DEADLINE_EXCEEDED = "deadline_exceeded"
    CANCELLED = "cancelled"
    WORKER_FAILED = "worker_failed"
    CLEANUP_FAILED = "cleanup_failed"
    JOB_NOT_FOUND = "job_not_found"
    SERIALIZATION_FAILED = "serialization_failed"
    INTERNAL_ERROR = "internal_error"
