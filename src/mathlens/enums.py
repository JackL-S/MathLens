"""公开契约枚举；枚举存在不代表后端已支持该能力。"""

from enum import StrEnum


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


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OutputFormat(StrEnum):
    TEXT = "text"
    LATEX = "latex"
    JSON = "json"
