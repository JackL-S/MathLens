"""运算求解相关enums"""

from enum import StrEnum

class Operation(StrEnum):
    """S1 支持的数学运算。"""
    CALCULATE = "calculate"
    SOLVE_EQUATION = "solve_equation"

class CalculationType(StrEnum):
    """计算操作具体类型"""
    EVALUATE = "evaluate"
    SIMPLIFY = "simplify"
    DIFFERENTIATE = "differentiate"
    INTEGRATE = "integrate"
    LIMIT = "limit"

class Domain(StrEnum):
    """求解集合"""
    REAL = "real"
    COMPLEX = "complex"
    INTEGER = "integer"

class Status(StrEnum):
    """求解状态"""
    SUCCESS = "success"
    NEEDS_INPUT = "needs_input"
    UNSUPPORTED = "unsupported"
    ERROR = "error"
    TIMEOUT = "timeout"

class ResultKind(StrEnum):
    """结果类型"""
    EXACT = "exact"
    MIXED = "mixed"
    UNEVALUATED = "unevaluated"
    NONE = "none"

class Completeness(StrEnum):
    """结果完成度"""
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"

class MessageType(StrEnum):
    """消息类型"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class ProcessingStage(StrEnum):
    """计算的阶段"""
    PREPARE = "prepare"
    COMPUTE = "compute"
    EXECUTION = "execution"

