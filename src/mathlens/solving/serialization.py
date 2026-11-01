"""内部数学对象转公开模型，JSON 编码由 codec 负责。"""

from sympy import Basic, latex

from ..schemas import MathExpression


def expression_to_display(expression: Basic) -> MathExpression:
    return MathExpression(latex=latex(expression), text=str(expression))
