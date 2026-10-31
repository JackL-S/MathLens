"""运算规格及其专属参数；不包含执行策略或计算实现。"""

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from ..enums import Domain, LimitDirection, Operation


@dataclass(frozen=True, kw_only=True)
class Substitution:
    variable: str
    value: str  # LaTeX，避免通过机器浮点数输入精确小数。


@dataclass(frozen=True, kw_only=True)
class EvaluateSpec:
    substitutions: tuple[Substitution, ...] = ()
    kind: Literal[Operation.EVALUATE] = field(default=Operation.EVALUATE, init=False)


@dataclass(frozen=True, kw_only=True)
class SimplifySpec:
    kind: Literal[Operation.SIMPLIFY] = field(default=Operation.SIMPLIFY, init=False)


@dataclass(frozen=True, kw_only=True)
class DifferentiationTarget:
    variable: str
    order: int = 1


@dataclass(frozen=True, kw_only=True)
class DifferentiateSpec:
    """targets 按顺序应用；空值允许准备阶段推断或请求补充。"""

    targets: tuple[DifferentiationTarget, ...] = ()
    kind: Literal[Operation.DIFFERENTIATE] = field(
        default=Operation.DIFFERENTIATE, init=False,
    )


@dataclass(frozen=True, kw_only=True)
class IntegrationLimit:
    """上下限均为空表示不定积分；只填一个是参数不完整。"""

    variable: str
    lower: str | None = None
    upper: str | None = None


@dataclass(frozen=True, kw_only=True)
class IntegrateSpec:
    """limits 从内到外排列；普通积分，不隐含柯西主值。"""

    limits: tuple[IntegrationLimit, ...] = ()
    kind: Literal[Operation.INTEGRATE] = field(default=Operation.INTEGRATE, init=False)


@dataclass(frozen=True, kw_only=True)
class SearchInterval:
    variable: str
    lower: str
    upper: str


@dataclass(frozen=True, kw_only=True)
class NumericOptions:
    """区间或初值不保证找到所有根；精度为十进制有效位数。"""

    significant_digits: int = 30
    search_intervals: tuple[SearchInterval, ...] = ()
    initial_values: tuple[Substitution, ...] = ()


@dataclass(frozen=True, kw_only=True)
class SolveSpec:
    unknowns: tuple[str, ...] = ()
    solution_domain: Domain = Domain.REAL
    numeric: NumericOptions | None = None
    kind: Literal[Operation.SOLVE_EQUATION] = field(
        default=Operation.SOLVE_EQUATION, init=False,
    )


@dataclass(frozen=True, kw_only=True)
class LimitSpec:
    variable: str | None = None
    point: str | None = None
    direction: LimitDirection = LimitDirection.BOTH
    kind: Literal[Operation.LIMIT] = field(default=Operation.LIMIT, init=False)


OperationSpec: TypeAlias = (
    EvaluateSpec | SimplifySpec | DifferentiateSpec
    | IntegrateSpec | SolveSpec | LimitSpec
)
