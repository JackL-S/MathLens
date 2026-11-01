"""独立 OCR 入口，也可由应用准备流程调用。"""

from ..control import ExecutionControl
from ..schemas import ExecutionOptions, RecognitionRequest, RecognitionResponse


def recognize(
    request: RecognitionRequest,
    *,
    options: ExecutionOptions | None = None,
    control: ExecutionControl | None = None,
) -> RecognitionResponse:
    """返回区域与候选；置信度未知为 None，不替用户确认数学含义。"""
    raise NotImplementedError
