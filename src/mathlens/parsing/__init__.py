"""LaTeX 输入适配；错误由应用边界转换为公开诊断。"""

from ..enums import DiagnosticCode, PreparationStatus


class MathInputError(ValueError):
    def __init__(
        self, message: str, *, code: DiagnosticCode = DiagnosticCode.INVALID_LATEX,
        status: PreparationStatus = PreparationStatus.ERROR,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
