"""基础数学表示、JSON 类型与契约版本。"""

from dataclasses import dataclass
from typing import TypeAlias


SCHEMA_VERSION = 1


PROTOCOL_VERSION = 1


JSONValue: TypeAlias = (
    str | int | float | bool | None
    | list["JSONValue"] | dict[str, "JSONValue"]
)


@dataclass(frozen=True, kw_only=True)
class MathExpression:
    """数学内容的公开表示，不是 Python/SymPy 可执行代码。"""

    latex: str
    text: str
