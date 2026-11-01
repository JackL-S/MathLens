"""运算规格及自身参数校验；不解析公式、不构造应用响应。"""

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from ..enums import DiagnosticCode, Domain, LimitDirection, Operation, ValidationIssueKind
from .validation import (
    ValidationIssue, invalid as _invalid, items_issues as _items, matches_type,
    missing as _missing, positive_int_issues as _positive_int, text_issues as _text,
)


def _duplicates(names: tuple[str, ...], path: str) -> tuple[ValidationIssue, ...]:
    issues = []
    seen = set()
    for index, name in enumerate(names):
        if name in seen:
            issues.extend(_invalid(f"{path}/{index}", "变量不能重复"))
        seen.add(name)
    return tuple(issues)


@dataclass(frozen=True, kw_only=True)
class Substitution:
    variable: str
    value: str  # LaTeX，避免通过机器浮点数输入精确小数。

    def validate(self) -> tuple[ValidationIssue, ...]:
        return (
            _text(self.variable, "/variable", "变量名", missing_code=DiagnosticCode.MISSING_VARIABLE)
            + _text(self.value, "/value", "代入值")
        )


@dataclass(frozen=True, kw_only=True)
class EvaluateSpec:
    substitutions: tuple[Substitution, ...] = ()
    kind: Literal[Operation.EVALUATE] = field(default=Operation.EVALUATE, init=False)

    def validate(self) -> tuple[ValidationIssue, ...]:
        issues = _items(
            self.substitutions, Substitution, "/substitutions", lambda item: item.validate(),
        )
        if issues:
            return issues
        names = tuple(item.variable for item in self.substitutions)
        # 重复问题定位到条目中的变量名，而不是集合本身。
        return tuple(
            ValidationIssue(
                kind=issue.kind, code=issue.code, message=issue.message,
                field_path=issue.field_path + "/variable",
            ) for issue in _duplicates(names, "/substitutions")
        )


@dataclass(frozen=True, kw_only=True)
class SimplifySpec:
    kind: Literal[Operation.SIMPLIFY] = field(default=Operation.SIMPLIFY, init=False)

    def validate(self) -> tuple[ValidationIssue, ...]:
        return ()


@dataclass(frozen=True, kw_only=True)
class DifferentiationTarget:
    variable: str
    order: int = 1

    def validate(self) -> tuple[ValidationIssue, ...]:
        return (
            _text(self.variable, "/variable", "求导变量", missing_code=DiagnosticCode.MISSING_VARIABLE)
            + _positive_int(self.order, "/order", "求导阶数")
        )


@dataclass(frozen=True, kw_only=True)
class DifferentiateSpec:
    """targets 按顺序应用；空值允许准备阶段推断或请求补充。"""

    targets: tuple[DifferentiationTarget, ...] = ()
    kind: Literal[Operation.DIFFERENTIATE] = field(
        default=Operation.DIFFERENTIATE, init=False,
    )

    def validate(self) -> tuple[ValidationIssue, ...]:
        if self.targets == ():
            return _missing("/targets", "请指定求导变量", DiagnosticCode.MISSING_VARIABLE)
        return _items(
            self.targets, DifferentiationTarget, "/targets", lambda item: item.validate(),
        )


@dataclass(frozen=True, kw_only=True)
class IntegrationLimit:
    """上下限均为空表示不定积分；只填一个是参数不完整。"""

    variable: str
    lower: str | None = None
    upper: str | None = None

    def validate(self) -> tuple[ValidationIssue, ...]:
        issues = _text(
            self.variable, "/variable", "积分变量", missing_code=DiagnosticCode.MISSING_VARIABLE,
        )
        for name, value in (("lower", self.lower), ("upper", self.upper)):
            if value is not None:
                issues += _text(value, f"/{name}", "积分边界")
        if (self.lower is None) != (self.upper is None):
            path = "/lower" if self.lower is None else "/upper"
            issues += _missing(path, "请补充配对的积分边界", DiagnosticCode.MISSING_BOUND)
        return issues


@dataclass(frozen=True, kw_only=True)
class IntegrateSpec:
    """limits 从内到外排列；普通积分，不隐含柯西主值。"""

    limits: tuple[IntegrationLimit, ...] = ()
    kind: Literal[Operation.INTEGRATE] = field(default=Operation.INTEGRATE, init=False)

    def validate(self) -> tuple[ValidationIssue, ...]:
        if self.limits == ():
            return _missing("/limits", "请指定积分变量", DiagnosticCode.MISSING_VARIABLE)
        return _items(
            self.limits, IntegrationLimit, "/limits", lambda item: item.validate(),
        )


@dataclass(frozen=True, kw_only=True)
class SearchInterval:
    variable: str
    lower: str
    upper: str

    def validate(self) -> tuple[ValidationIssue, ...]:
        # 上下界为数学文本，大小关系由解析阶段判断。
        return (
            _text(self.variable, "/variable", "搜索变量", missing_code=DiagnosticCode.MISSING_VARIABLE)
            + _text(self.lower, "/lower", "搜索下界")
            + _text(self.upper, "/upper", "搜索上界")
        )


@dataclass(frozen=True, kw_only=True)
class NumericOptions:
    """区间或初值不保证找到所有根；精度为十进制有效位数。"""

    significant_digits: int = 30
    search_intervals: tuple[SearchInterval, ...] = ()
    initial_values: tuple[Substitution, ...] = ()

    def validate(self) -> tuple[ValidationIssue, ...]:
        initial_issues = _items(
            self.initial_values, Substitution, "/initial_values", lambda item: item.validate(),
        )
        issues = (
            _positive_int(self.significant_digits, "/significant_digits", "有效位数")
            + _items(
                self.search_intervals, SearchInterval, "/search_intervals",
                lambda item: item.validate(),
            )
            + initial_issues
        )
        if not initial_issues:
            names = tuple(item.variable for item in self.initial_values)
            issues += tuple(
                ValidationIssue(
                    kind=issue.kind, code=issue.code, message=issue.message,
                    field_path=issue.field_path + "/variable",
                ) for issue in _duplicates(names, "/initial_values")
            )
        return issues


@dataclass(frozen=True, kw_only=True)
class SolveSpec:
    unknowns: tuple[str, ...] = ()
    solution_domain: Domain = Domain.REAL
    numeric: NumericOptions | None = None
    kind: Literal[Operation.SOLVE_EQUATION] = field(
        default=Operation.SOLVE_EQUATION, init=False,
    )

    def validate(self) -> tuple[ValidationIssue, ...]:
        unknown_issues: tuple[ValidationIssue, ...] = ()
        if not matches_type(self.unknowns, tuple):
            unknown_issues += _invalid("/unknowns", "未知量必须是元组")
        elif not self.unknowns:
            unknown_issues += _missing("/unknowns", "请指定未知量", DiagnosticCode.MISSING_VARIABLE)
        else:
            for index, variable in enumerate(self.unknowns):
                unknown_issues += _text(
                    variable, f"/unknowns/{index}", "未知量",
                    missing_code=DiagnosticCode.MISSING_VARIABLE,
                )
            if not unknown_issues:
                unknown_issues += _duplicates(self.unknowns, "/unknowns")
        issues = unknown_issues
        if not matches_type(self.solution_domain, Domain):
            issues += _invalid("/solution_domain", "求解范围必须是 Domain")
        if self.numeric is not None:
            if not matches_type(self.numeric, NumericOptions):
                issues += _invalid("/numeric", "数值参数必须是 NumericOptions")
            else:
                numeric_issues = self.numeric.validate()
                issues += tuple(issue.prefixed("/numeric") for issue in numeric_issues)
                if not unknown_issues and not numeric_issues:
                    for name in ("search_intervals", "initial_values"):
                        for index, item in enumerate(getattr(self.numeric, name)):
                            if item.variable not in self.unknowns:
                                issues += (ValidationIssue(
                                    kind=ValidationIssueKind.CONFLICT,
                                    code=DiagnosticCode.CONFLICTING_ARGUMENTS,
                                    message="数值参数的变量必须属于求解未知量",
                                    field_path=f"/numeric/{name}/{index}/variable",
                                ),)
        return issues


@dataclass(frozen=True, kw_only=True)
class LimitSpec:
    variable: str | None = None
    point: str | None = None
    direction: LimitDirection = LimitDirection.BOTH
    kind: Literal[Operation.LIMIT] = field(default=Operation.LIMIT, init=False)

    def validate(self) -> tuple[ValidationIssue, ...]:
        issues: tuple[ValidationIssue, ...] = ()
        for name, value, code, label in (
            ("variable", self.variable, DiagnosticCode.MISSING_VARIABLE, "极限变量"),
            ("point", self.point, DiagnosticCode.MISSING_FIELD, "趋近点"),
        ):
            if value is None:
                issues += _missing(f"/{name}", f"请补充{label}", code)
            else:
                issues += _text(value, f"/{name}", label, missing_code=code)
        if not matches_type(self.direction, LimitDirection):
            issues += _invalid("/direction", "极限方向必须是 LimitDirection")
        return issues


OperationSpec: TypeAlias = (
    EvaluateSpec | SimplifySpec | DifferentiateSpec
    | IntegrateSpec | SolveSpec | LimitSpec
)
