"""只清理外部格式包装，不修补数学语法。"""

from ..schemas import NormalizationChange
from . import MathInputError


def normalize_latex(latex: str) -> tuple[str, tuple[NormalizationChange, ...]]:
    changes = []
    normalized = latex.strip()
    if normalized != latex:
        changes.append(NormalizationChange(
            code="trim_outer_whitespace", before=latex, after=normalized,
        ))
    for left, right in (("$$", "$$"), ("$", "$"), (r"\[", r"\]"), (r"\(", r"\)")):
        if normalized.startswith(left) or normalized.endswith(right):
            if not (normalized.startswith(left) and normalized.endswith(right)):
                raise MathInputError("公式定界符不配对")
            if len(normalized) < len(left) + len(right):
                raise MathInputError("公式定界符不完整")
            before = normalized
            normalized = normalized[len(left):-len(right)].strip()
            changes.append(NormalizationChange(
                code="remove_math_delimiters", before=before, after=normalized,
            ))
            break
    if not normalized:
        raise MathInputError("公式不能为空")
    return normalized, tuple(changes)
