"""固定 latex2sympy2 组合的标量算术适配，转换前检查语法结构。"""

from dataclasses import dataclass

import latex2sympy2 as backend
from antlr4 import Token
from antlr4.error.ErrorListener import ErrorListener
from sympy import Add, Expr, Float, Integer, Mul, Ne, Pow, Rational, Symbol, preorder_traversal
from sympy.core.relational import Relational

from ..enums import DiagnosticCode, PreparationStatus
from . import MathInputError


@dataclass(frozen=True)
class ParsedExpression:
    expression: Expr
    conditions: tuple[Relational, ...]


class _SyntaxErrors(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise MathInputError(f"公式语法错误（第 {line} 行，第 {column + 1} 列）")


def _unavailable(message: str) -> MathInputError:
    return MathInputError(
        message, code=DiagnosticCode.CAPABILITY_UNAVAILABLE,
        status=PreparationStatus.UNSUPPORTED,
    )


def parse_expression(latex: str) -> ParsedExpression:
    lexer = backend.PSLexer(backend.InputStream(latex))
    lexer.removeErrorListeners()
    lexer.addErrorListener(_SyntaxErrors())
    tokens = backend.CommonTokenStream(lexer)
    parser = backend.PSParser(tokens)
    parser.removeErrorListeners()
    parser.addErrorListener(_SyntaxErrors())
    tree = parser.math()
    if tokens.LA(1) != Token.EOF:
        raise MathInputError("公式存在未解析的内容")
    relation = tree.relation()
    if relation is None or relation.expr() is None:
        raise _unavailable("当前化简切片只接受表达式，不接受方程或关系式")

    # 使用解析器提供的语法树检查能力，不另写数学词法或语法。
    blocked = {
        "func", "matrix", "det", "norm_group", "abs_group", "floor_group",
        "ceil_group", "eval_at", "postfix_op", "binom", "mathit",
    }
    stack = [tree]
    while stack:
        node = stack.pop()
        if hasattr(node, "getRuleIndex"):
            rule = parser.ruleNames[node.getRuleIndex()]
            if rule in blocked:
                raise _unavailable("当前切片仅支持算术、变量、整数幂和分式")
        if hasattr(node, "symbol"):
            if node.symbol.type in (backend.PSLexer.DIFFERENTIAL, backend.PSLexer.VARIABLE) or node.getText() == r"\partial":
                raise _unavailable("当前切片不处理内嵌微分运算")
        stack.extend(getattr(node, "children", None) or ())

    try:
        # 避开 convert_relation：该接口可能提前解方程并修改库的全局状态。
        expression = backend.convert_expr(relation.expr())
    except MathInputError:
        raise
    except Exception as exc:
        raise MathInputError("解析器处理失败", code=DiagnosticCode.PARSER_FAILED) from exc
    if not isinstance(expression, Expr) or expression.is_Matrix:
        raise _unavailable("当前仅支持标量表达式")

    conditions = []
    allowed = (Add, Mul, Pow, Symbol, Rational, Integer)
    for node in preorder_traversal(expression):
        if node in (backend.sympy.pi, backend.sympy.E, backend.sympy.I):
            continue
        if not isinstance(node, allowed) or isinstance(node, Float):
            raise _unavailable("当前仅支持精确标量算术表达式")
        if isinstance(node, Pow):
            if node.exp.is_integer is not True:
                raise _unavailable("非整数幂的分支与定义域暂未接入")
            if node.base.is_zero is True and node.exp.is_zero is True:
                raise _unavailable("当前尚未约定 0^0 的含义")
            if node.exp.is_negative:
                if node.base.is_zero is True:
                    raise MathInputError("原式包含除零", code=DiagnosticCode.RESULT_VALIDATION_FAILED)
                if node.base.is_nonzero is not True:
                    condition = Ne(node.base, 0, evaluate=False)
                    if condition not in conditions:
                        conditions.append(condition)
    return ParsedExpression(expression, tuple(conditions))
