"""用户请求、符号假设、结果偏好和已确认的问题快照。"""

from dataclasses import dataclass, field

from ..enums import MethodPolicy
from .base import SCHEMA_VERSION
from .inputs import InputSpec
from .operations import OperationSpec


@dataclass(frozen=True, kw_only=True)
class SymbolAssumptions:
    """None 表示未声明；矛盾声明由准备层拒绝。"""

    real: bool | None = None
    integer: bool | None = None
    positive: bool | None = None
    nonnegative: bool | None = None
    nonzero: bool | None = None


@dataclass(frozen=True, kw_only=True)
class SymbolDeclaration:
    name: str
    latex: str | None = None
    assumptions: SymbolAssumptions = field(default_factory=SymbolAssumptions)


@dataclass(frozen=True, kw_only=True)
class ResultPreferences:
    method: MethodPolicy = MethodPolicy.SYMBOLIC_FIRST
    include_approximation: bool = False
    significant_digits: int = 30
    include_steps: bool = False


@dataclass(frozen=True, kw_only=True)
class ComputeRequest:
    """用户意图；operation=None 请求推断，不等于可直接求解。"""

    input: InputSpec
    operation: OperationSpec | None = None
    symbols: tuple[SymbolDeclaration, ...] = ()
    preferences: ResultPreferences = field(default_factory=ResultPreferences)
    schema_version: int = SCHEMA_VERSION


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
