"""诊断信息与需要用户补充或确认的输入项。"""

from dataclasses import dataclass

from ..enums import MessageType, ProcessingStage
from .operations import OperationSpec


@dataclass(frozen=True, kw_only=True)
class Diagnostic:
    """内部 code 使用 DiagnosticCode，外部未知代码保留为字符串。

    field_paths 相对当前入口的输入文档定位字段。
    """

    code: str
    message: str
    severity: MessageType
    stage: ProcessingStage
    field_paths: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class InputChoice:
    choice_id: str
    label: str
    latex: str | None = None
    operation: OperationSpec | None = None


@dataclass(frozen=True, kw_only=True)
class InputRequest:
    """code 复用 DiagnosticCode；修改字段后重新 prepare。

    外部未知代码保留为字符串；choice_id 不是可执行令牌。
    """

    code: str
    message: str
    field_path: str
    choices: tuple[InputChoice, ...] = ()
