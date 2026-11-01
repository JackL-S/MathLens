"""纵向切片的符号化简。"""

from sympy import Expr, S, simplify


def simplify_expression(expression: Expr) -> Expr:
    result = simplify(expression)
    if result.has(S.NaN, S.ComplexInfinity, S.Infinity, S.NegativeInfinity):
        raise ValueError("化简没有得到已定义的有限表达式")
    return result
