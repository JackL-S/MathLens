"""OCR 请求、识别区域、公式候选与响应。"""

from dataclasses import dataclass, field
from typing import Literal

from ..enums import Status
from .base import SCHEMA_VERSION
from .diagnostics import Diagnostic
from .inputs import ImageInput, ImageRegion


@dataclass(frozen=True, kw_only=True)
class RecognitionCandidate:
    candidate_id: str
    latex: str
    confidence: float | None = None


@dataclass(frozen=True, kw_only=True)
class RecognizedRegion:
    region_id: str
    region: ImageRegion
    candidates: tuple[RecognitionCandidate, ...]


@dataclass(frozen=True, kw_only=True)
class RecognitionRequest:
    input: ImageInput
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True, kw_only=True)
class RecognitionResponse:
    status: Status
    regions: tuple[RecognizedRegion, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    schema_version: int = SCHEMA_VERSION
    kind: Literal["recognition"] = field(default="recognition", init=False)
