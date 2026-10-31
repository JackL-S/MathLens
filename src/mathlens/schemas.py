"""计算请求、执行描述与公开结果的数据结构。"""

from dataclasses import dataclass, field
from typing import TypeAlias
from .enums import (
    CalculationType,
    Completeness,
    Domain,
    Operation,
    ResultKind,
    Status,
    MessageType,
    ProcessingStage
)

# json 用于结果输出
JSONValue: TypeAlias = (
    str
    | int
    | float
    | bool
    | None
    | list["JSONValue"]
    | dict[str, "JSONValue"]
)

@dataclass
class ComputeRequest:
    """
    用户提交的计算请求。
    Attributes:
        latex: 原始 LaTeX 公式。
        operation: 执行计算或解方程。
        variables: 目标变量名。
        domain: 求解范围
        calculation_type: 具体计算操作，解方程时为空。
    """
    latex: str
    operation: Operation
    variables: str
    domain: Domain
    # 默认值为None,对应解方程的运算
    calculation_type: CalculationType | None = None

@dataclass
class ComputeMessage:
    """计算Message"""
    message: str
    severity: MessageType
    stage: ProcessingStage

@dataclass
class ComputeResponse:
    """
    一次计算请求的统一响应。
    Attributes:
        status: 请求处理状态。
        result_kind: 数学结果的性质。
        completeness: 解集完整性。
        value: 结构化数学答案。
        latex: 用于展示的完整答案。
        domain: 实际使用的定义域。
        conditions: 答案成立的条件。
        messages: 请求处理过程中产生的消息。
        attempts: 计算方法和耗时等执行记录。
    """
    status: Status
    result_kind: ResultKind = ResultKind.NONE
    completeness: Completeness = Completeness.NOT_APPLICABLE
    value: dict[str, JSONValue] | None = None
    latex: str | None = None
    domain: Domain | None = None
    conditions: list[dict[str, str]] = field(default_factory=list)
    messages: list[ComputeMessage] = field(default_factory=list)
    attempts: list[dict[str, JSONValue]] = field(default_factory=list)