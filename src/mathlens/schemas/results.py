"""数学结果、成立条件、近似值、步骤与计算响应。"""

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from ..enums import Completeness, ResultKind, Status, StepsStatus
from .base import SCHEMA_VERSION, MathExpression
from .diagnostics import Diagnostic, InputRequest
from .preparation import PreparationResponse
from .requests import PreparedProblem


@dataclass(frozen=True, kw_only=True)
class ExpressionValue:
    expression: MathExpression
    result_kind: ResultKind = ResultKind.EXACT
    kind: Literal["expression"] = field(default="expression", init=False)


@dataclass(frozen=True, kw_only=True)
class FiniteSetValue:
    """elements=() 表示空集；完整性由响应 completeness 决定。"""

    elements: tuple[ExpressionValue, ...]
    kind: Literal["finite_set"] = field(default="finite_set", init=False)


@dataclass(frozen=True, kw_only=True)
class SymbolicSetValue:
    expression: MathExpression
    kind: Literal["symbolic_set"] = field(default="symbolic_set", init=False)


@dataclass(frozen=True, kw_only=True)
class Assignment:
    variable: str
    value: ExpressionValue


@dataclass(frozen=True, kw_only=True)
class MathCondition:
    """scope 非空时相对 ComputeResponse；空串作用于所属结果、分支或步骤。"""

    expression: MathExpression
    scope: str = ""


@dataclass(frozen=True, kw_only=True)
class SolutionBranch:
    assignments: tuple[Assignment, ...]
    conditions: tuple[MathCondition, ...] = ()


@dataclass(frozen=True, kw_only=True)
class SolutionAssignmentsValue:
    solutions: tuple[SolutionBranch, ...]
    kind: Literal["solution_assignments"] = field(
        default="solution_assignments", init=False,
    )


@dataclass(frozen=True, kw_only=True)
class DivergentValue:
    direction: Literal["positive_infinity", "negative_infinity", "does_not_exist"]
    kind: Literal["divergent"] = field(default="divergent", init=False)


@dataclass(frozen=True, kw_only=True)
class UnevaluatedValue:
    expression: MathExpression
    kind: Literal["unevaluated"] = field(default="unevaluated", init=False)


MathValue: TypeAlias = (
    ExpressionValue | FiniteSetValue | SymbolicSetValue
    | SolutionAssignmentsValue | DivergentValue | UnevaluatedValue
)


@dataclass(frozen=True, kw_only=True)
class Approximation:
    """单个数值近似；target 指向主结果项，不替换精确主结果。"""

    target: str
    value: MathExpression
    significant_digits: int
    absolute_error_bound: str | None = None


@dataclass(frozen=True, kw_only=True)
class CalculationStep:
    rule_code: str
    explanation: str
    before: MathExpression
    after: MathExpression
    conditions: tuple[MathCondition, ...] = ()
    children: tuple["CalculationStep", ...] = ()


@dataclass(frozen=True, kw_only=True)
class StepsResult:
    status: StepsStatus = StepsStatus.NOT_REQUESTED
    items: tuple[CalculationStep, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True, kw_only=True)
class ComputationAttempt:
    method: str
    status: Status
    elapsed_seconds: float
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True, kw_only=True)
class ComputeResponse:
    """执行状态、数学性质、完整性分别表达；中止时可含部分结果。"""

    status: Status
    problem: PreparedProblem | None = None
    result_kind: ResultKind = ResultKind.NONE
    completeness: Completeness = Completeness.NOT_APPLICABLE
    value: MathValue | None = None
    latex: str | None = None
    conditions: tuple[MathCondition, ...] = ()
    approximations: tuple[Approximation, ...] = ()
    steps: StepsResult = field(default_factory=StepsResult)
    input_requests: tuple[InputRequest, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    attempts: tuple[ComputationAttempt, ...] = ()
    schema_version: int = SCHEMA_VERSION
    kind: Literal["computation"] = field(default="computation", init=False)


ApplicationResponse: TypeAlias = PreparationResponse | ComputeResponse
