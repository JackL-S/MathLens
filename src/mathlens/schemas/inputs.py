"""公式输入、图片区域与资源标识。"""

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from ..enums import DiagnosticCode
from .base import SCHEMA_VERSION
from .validation import (
    ValidationIssue, invalid, model_issues, positive_int_issues, text_issues,
)


@dataclass(frozen=True, kw_only=True)
class ImageRegion:
    """相对原始图像左上角的像素矩形，宽高为正且不得越界。"""

    x: int
    y: int
    width: int
    height: int

    def validate(self) -> tuple[ValidationIssue, ...]:
        return (
            positive_int_issues(self.x, "/x", "横坐标", minimum=0)
            + positive_int_issues(self.y, "/y", "纵坐标", minimum=0)
            + positive_int_issues(self.width, "/width", "区域宽度")
            + positive_int_issues(self.height, "/height", "区域高度")
        )


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

    def validate(self) -> tuple[ValidationIssue, ...]:
        issues = text_issues(self.media_id, "/media_id", "图片资源标识")
        if self.region is not None:
            issues += model_issues(self.region, ImageRegion, "/region", lambda region: region.validate())
        return issues


@dataclass(frozen=True, kw_only=True)
class LatexInput:
    latex: str
    source: "ImageInput | None" = None
    kind: Literal["latex"] = field(default="latex", init=False)

    def validate(self) -> tuple[ValidationIssue, ...]:
        issues = text_issues(
            self.latex, "/latex", "LaTeX 公式", empty_code=DiagnosticCode.INVALID_LATEX,
        )
        if self.source is not None:
            issues += model_issues(self.source, ImageInput, "/source", lambda image: image.validate())
        return issues


InputSpec: TypeAlias = LatexInput | ImageInput


def input_issues(value: object) -> tuple[ValidationIssue, ...]:
    """输入模型的运行时分流边界，路径相对输入模型。"""
    if isinstance(value, LatexInput):
        return value.validate()
    if isinstance(value, ImageInput):
        return value.validate()
    return invalid("", "输入必须是 LatexInput 或 ImageInput")
