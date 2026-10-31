"""准备阶段响应；请求与快照模型位于 requests。"""

from dataclasses import dataclass, field
from typing import Literal

from ..enums import PreparationStatus
from .base import SCHEMA_VERSION, MathExpression
from .diagnostics import Diagnostic, InputRequest
from .requests import PreparedProblem


@dataclass(frozen=True, kw_only=True)
class PreparationResponse:
    status: PreparationStatus
    problem: PreparedProblem | None = None
    preview: MathExpression | None = None
    input_requests: tuple[InputRequest, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    schema_version: int = SCHEMA_VERSION
    kind: Literal["preparation"] = field(default="preparation", init=False)
