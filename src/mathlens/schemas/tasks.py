"""执行配置、能力声明与任务数据；与实际进程执行分开。"""

from dataclasses import dataclass, field, fields
from typing import Literal, TypeAlias

from ..enums import Domain, MethodPolicy, Operation, ProcessingStage
from .base import PROTOCOL_VERSION, SCHEMA_VERSION
from .requests import ComputeRequest, PreparedProblem
from .results import ApplicationResponse
from .validation import (
    ValidationIssue, boolean_issues, model_issues, positive_int_issues,
    positive_number_issues, version_issues,
)


@dataclass(frozen=True, kw_only=True)
class ResourceLimits:
    max_input_bytes: int = 1_000_000
    max_output_bytes: int = 4_000_000
    max_json_depth: int = 64
    max_significant_digits: int = 1_000
    max_image_pixels: int = 20_000_000
    max_derivative_order: int = 100
    max_steps: int = 1_000

    def validate(self) -> tuple[ValidationIssue, ...]:
        return tuple(
            issue for item in fields(self)
            for issue in positive_int_issues(getattr(self, item.name), f"/{item.name}", "容量限制")
        )



@dataclass(frozen=True, kw_only=True)
class ExecutionOptions:
    """总时限不按阶段重置；清理余量单列。大小限制为正整数。"""

    timeout_seconds: float = 30.0
    cleanup_timeout_seconds: float = 2.0
    allow_partial_result: bool = False
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    schema_version: int = SCHEMA_VERSION

    def validate(self) -> tuple[ValidationIssue, ...]:
        return (
            version_issues(self.schema_version, SCHEMA_VERSION)
            + positive_number_issues(self.timeout_seconds, "/timeout_seconds")
            + positive_number_issues(self.cleanup_timeout_seconds, "/cleanup_timeout_seconds")
            + boolean_issues(self.allow_partial_result, "/allow_partial_result", "部分结果选项")
            + model_issues(self.limits, ResourceLimits, "/limits", lambda value: value.validate())
        )



@dataclass(frozen=True, kw_only=True)
class ProgressEvent:
    stage: ProcessingStage
    message: str
    fraction: float | None = None



@dataclass(frozen=True, kw_only=True)
class OperationCapability:
    operation: Operation
    methods: tuple[MethodPolicy, ...]
    supports_steps: bool = False
    solution_domains: tuple[Domain, ...] = ()
    max_variables: int | None = None



@dataclass(frozen=True, kw_only=True)
class Capabilities:
    """只列已实现且启用的能力；空 operations 不表示全部支持。"""

    operations: tuple[OperationCapability, ...] = ()
    input_kinds: tuple[Literal["latex", "image"], ...] = ()
    supports_assumptions: bool = False
    supports_cancellation: bool = False
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    schema_version: int = SCHEMA_VERSION



@dataclass(frozen=True, kw_only=True)
class PrepareTask:
    request: ComputeRequest
    kind: Literal["prepare"] = field(default="prepare", init=False)


@dataclass(frozen=True, kw_only=True)
class ComputeTask:
    problem: PreparedProblem
    kind: Literal["compute"] = field(default="compute", init=False)


@dataclass(frozen=True, kw_only=True)
class RunTask:
    request: ComputeRequest
    kind: Literal["run"] = field(default="run", init=False)


WorkerTask: TypeAlias = PrepareTask | ComputeTask | RunTask


@dataclass(frozen=True, kw_only=True)
class WorkerRequest:
    task: WorkerTask
    options: ExecutionOptions
    protocol_version: int = PROTOCOL_VERSION


@dataclass(frozen=True, kw_only=True)
class WorkerResult:
    response: ApplicationResponse
    protocol_version: int = PROTOCOL_VERSION
