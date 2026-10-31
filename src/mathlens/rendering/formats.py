"""展示接口，只消费公开结果，不补算答案、步骤或近似值。"""

from ..enums import OutputFormat
from ..schemas import WorkerResponse


def render(response: WorkerResponse, *, output_format: OutputFormat) -> str:
    """组织文本、LaTeX 或 JSON；JSON 与 codec 使用同一公开契约。

    错误响应也可展示；不支持的格式抛 ValueError。
    """
    raise NotImplementedError
