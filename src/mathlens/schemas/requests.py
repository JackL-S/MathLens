"""用户请求、符号假设、结果偏好和已确认的问题快照。"""

from dataclasses import dataclass, field, fields

from ..enums import DiagnosticCode, MethodPolicy, ValidationIssueKind
from .base import SCHEMA_VERSION
from .inputs import InputSpec, input_issues
from .operations import OperationSpec, SolveSpec
from .validation import (
    ValidationIssue, boolean_issues, invalid, items_issues, matches_type, missing,
    model_issues, positive_int_issues, text_issues, version_issues,
)


@dataclass(frozen=True, kw_only=True)
class SymbolAssumptions:
    """None 表示未声明；矛盾声明由准备层拒绝。"""

    real: bool | None = None
    integer: bool | None = None
    positive: bool | None = None
    nonnegative: bool | None = None
    nonzero: bool | None = None

    def validate(self) -> tuple[ValidationIssue, ...]:
        issues = ()
        for item in fields(self):
            value = getattr(self, item.name)
            if value is not None:
                issues += boolean_issues(value, f"/{item.name}", "符号假设")
        if issues:
            return issues
        for premise, consequence in (
            ("integer", "real"), ("positive", "real"),
            ("positive", "nonnegative"), ("positive", "nonzero"),
            ("nonnegative", "real"),
        ):
            if getattr(self, premise) is True and getattr(self, consequence) is False:
                issues += (ValidationIssue(
                    kind=ValidationIssueKind.CONFLICT,
                    code=DiagnosticCode.CONFLICTING_ARGUMENTS,
                    message=f"{premise}=true 与 {consequence}=false 矛盾",
                    field_path=f"/{consequence}",
                ),)
        if self.nonnegative is True and self.nonzero is True and self.positive is False:
            issues += (ValidationIssue(
                kind=ValidationIssueKind.CONFLICT, code=DiagnosticCode.CONFLICTING_ARGUMENTS,
                message="非负且非零的符号应为正数", field_path="/positive",
            ),)
        return issues


@dataclass(frozen=True, kw_only=True)
class SymbolDeclaration:
    name: str
    latex: str | None = None
    assumptions: SymbolAssumptions = field(default_factory=SymbolAssumptions)

    def validate(self) -> tuple[ValidationIssue, ...]:
        issues = text_issues(self.name, "/name", "符号名")
        if self.latex is not None:
            issues += text_issues(self.latex, "/latex", "符号写法")
        return issues + model_issues(
            self.assumptions, SymbolAssumptions, "/assumptions", lambda value: value.validate(),
        )


@dataclass(frozen=True, kw_only=True)
class ResultPreferences:
    method: MethodPolicy = MethodPolicy.SYMBOLIC_FIRST
    include_approximation: bool = False
    significant_digits: int = 30
    include_steps: bool = False

    def validate(self) -> tuple[ValidationIssue, ...]:
        issues = positive_int_issues(self.significant_digits, "/significant_digits", "有效位数")
        if not matches_type(self.method, MethodPolicy):
            issues += invalid("/method", "计算策略必须是 MethodPolicy")
        return (
            issues
            + boolean_issues(self.include_approximation, "/include_approximation", "近似展示选项")
            + boolean_issues(self.include_steps, "/include_steps", "步骤选项")
        )


@dataclass(frozen=True, kw_only=True)
class ComputeRequest:
    """用户意图；operation=None 请求推断，不等于可直接求解。"""

    input: InputSpec
    operation: OperationSpec | None = None
    symbols: tuple[SymbolDeclaration, ...] = ()
    preferences: ResultPreferences = field(default_factory=ResultPreferences)
    schema_version: int = SCHEMA_VERSION

    def validate(self) -> tuple[ValidationIssue, ...]:
        """组合各模型校验并检查请求内关系，不读取外部资源或解析公式。"""
        issues = version_issues(self.schema_version, SCHEMA_VERSION)
        issues += tuple(issue.prefixed("/input") for issue in input_issues(self.input))
        if self.operation is None:
            issues += missing("/operation", "请选择要执行的运算", DiagnosticCode.MISSING_OPERATION)
        elif not matches_type(self.operation, OperationSpec):
            issues += invalid("/operation", "运算必须是对应的规格模型")
        else:
            issues += tuple(issue.prefixed("/operation") for issue in self.operation.validate())
        preference_issues = model_issues(
            self.preferences, ResultPreferences, "/preferences", lambda value: value.validate(),
        )
        symbol_issues = items_issues(
            self.symbols, SymbolDeclaration, "/symbols", lambda value: value.validate(),
        )
        issues += preference_issues + symbol_issues
        if not symbol_issues:
            seen = set()
            for index, symbol in enumerate(self.symbols):
                if symbol.name in seen:
                    issues += invalid(f"/symbols/{index}/name", "符号声明不能重复")
                seen.add(symbol.name)
        if (
            not preference_issues and isinstance(self.operation, SolveSpec)
            and self.preferences.method is MethodPolicy.SYMBOLIC_ONLY
            and self.operation.numeric is not None
        ):
            issues += (ValidationIssue(
                kind=ValidationIssueKind.CONFLICT, code=DiagnosticCode.CONFLICTING_ARGUMENTS,
                message="仅符号策略与显式数值求解参数冲突", field_path="/operation/numeric",
            ),)
        return issues


@dataclass(frozen=True, kw_only=True)
class NormalizationChange:
    code: str
    before: str
    after: str


@dataclass(frozen=True, kw_only=True)
class PreparedProblem:
    """无歧义、无第三方对象的快照；修改数学内容后必须重新准备。"""

    original_input: InputSpec
    latex: str
    operation: OperationSpec
    symbols: tuple[SymbolDeclaration, ...]
    preferences: ResultPreferences
    changes: tuple[NormalizationChange, ...] = ()
    schema_version: int = SCHEMA_VERSION
