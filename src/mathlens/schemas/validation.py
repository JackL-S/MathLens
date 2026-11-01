"""模型共用的校验问题与结构检查，不依赖具体模型或应用响应。"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from math import isfinite
from types import UnionType
from typing import TypeVar

from ..enums import DiagnosticCode, ValidationIssueKind


def matches_type(
    value: object,
    expected: type[object] | UnionType | tuple[type[object], ...],
) -> bool:
    """在运行时边界检查结构，不假设 dataclass 注解已经得到执行。"""
    return isinstance(value, expected)


def has_exact_type(value: object, expected: type[object]) -> bool:
    """检查精确类型，例如版本整数不能接受 bool。"""
    return type(value) is expected


@dataclass(frozen=True, kw_only=True)
class ValidationIssue:
    """field_path 相对被校验对象；应用层转换为请求字段路径。"""

    kind: ValidationIssueKind
    code: DiagnosticCode
    message: str
    field_path: str

    def prefixed(self, prefix: str) -> "ValidationIssue":
        """为嵌套对象附加 JSON Pointer 前缀，不修改原问题。"""
        return replace(self, field_path=prefix + self.field_path)


_Item = TypeVar("_Item")


def invalid(
    path: str, message: str, code: DiagnosticCode = DiagnosticCode.INVALID_REQUEST,
) -> tuple[ValidationIssue, ...]:
    return (ValidationIssue(
        kind=ValidationIssueKind.INVALID, code=code,
        message=message, field_path=path,
    ),)



def missing(path: str, message: str, code: DiagnosticCode) -> tuple[ValidationIssue, ...]:
    return (ValidationIssue(
        kind=ValidationIssueKind.MISSING, code=code,
        message=message, field_path=path,
    ),)



def text_issues(
    value: object, path: str, label: str,
    *, missing_code: DiagnosticCode | None = None,
    empty_code: DiagnosticCode = DiagnosticCode.INVALID_REQUEST,
) -> tuple[ValidationIssue, ...]:
    if not isinstance(value, str):
        return invalid(path, f"{label}必须是字符串")
    if not value.strip():
        if missing_code is not None:
            return missing(path, f"请补充{label}", missing_code)
        return invalid(path, f"{label}不能为空", empty_code)
    return ()



def positive_int_issues(
    value: object, path: str, label: str, *, minimum: int = 1,
) -> tuple[ValidationIssue, ...]:
    if type(value) is not int or value < minimum:
        return invalid(path, f"{label}必须是大于等于 {minimum} 的整数")
    return ()



def items_issues(
    value: object, item_type: type[_Item], path: str,
    validate: Callable[[_Item], tuple[ValidationIssue, ...]],
) -> tuple[ValidationIssue, ...]:
    if not isinstance(value, tuple):
        return invalid(path, "参数集合必须是元组")
    issues = []
    for index, item in enumerate(value):
        prefix = f"{path}/{index}"
        if not isinstance(item, item_type):
            issues.extend(invalid(prefix, f"参数必须是 {item_type.__name__}"))
        else:
            issues.extend(issue.prefixed(prefix) for issue in validate(item))
    return tuple(issues)


def model_issues(
    value: object, model_type: type[_Item], path: str,
    validate: Callable[[_Item], tuple[ValidationIssue, ...]],
) -> tuple[ValidationIssue, ...]:
    if not isinstance(value, model_type):
        return invalid(path, f"参数必须是 {model_type.__name__}")
    return tuple(issue.prefixed(path) for issue in validate(value))


def version_issues(value: object, expected: int) -> tuple[ValidationIssue, ...]:
    if not has_exact_type(value, int) or value != expected:
        return (ValidationIssue(
            kind=ValidationIssueKind.INVALID, code=DiagnosticCode.SCHEMA_VERSION_MISMATCH,
            message="公开契约版本不正确", field_path="/schema_version",
        ),)
    return ()


def boolean_issues(value: object, path: str, label: str) -> tuple[ValidationIssue, ...]:
    if not has_exact_type(value, bool):
        return invalid(path, f"{label}必须是布尔值")
    return ()


def positive_number_issues(value: object, path: str) -> tuple[ValidationIssue, ...]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return invalid(path, "时限必须是有限正数")
    try:
        finite = isfinite(value)
    except OverflowError:
        finite = False
    if not finite or value <= 0:
        return invalid(path, "时限必须是有限正数")
    return ()
