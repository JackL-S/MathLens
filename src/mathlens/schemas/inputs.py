"""公式输入、图片区域与资源标识。"""

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from .base import SCHEMA_VERSION


@dataclass(frozen=True, kw_only=True)
class ImageRegion:
    """相对原始图像左上角的像素矩形，宽高为正且不得越界。"""

    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True, kw_only=True)
class MediaResource:
    """输入资源层管理的标识，不能作为任意文件路径或 URL。"""

    media_id: str
    media_type: str
    width: int
    height: int
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True, kw_only=True)
class ImageInput:
    media_id: str
    region: ImageRegion | None = None
    kind: Literal["image"] = field(default="image", init=False)


@dataclass(frozen=True, kw_only=True)
class LatexInput:
    latex: str
    source: "ImageInput | None" = None
    kind: Literal["latex"] = field(default="latex", init=False)


InputSpec: TypeAlias = LatexInput | ImageInput
