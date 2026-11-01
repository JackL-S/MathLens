import pytest
from sympy import Rational, Symbol, simplify

from mathlens.enums import PreparationStatus
from mathlens.parsing import MathInputError
from mathlens.parsing.latex import parse_expression
from mathlens.parsing.normalize import normalize_latex


@pytest.mark.parametrize("source", ["  x+x  ", "$x+x$", "$$x+x$$", r"\(x+x\)", r"\[x+x\]"])
def test_normalize_preserves_original_and_records_changes(source):
    text, changes = normalize_latex(source)
    assert text == "x+x"
    assert changes[0].before == source
    assert changes[-1].after == "x+x"


@pytest.mark.parametrize("source", ["", "  ", "$$", "$x", "x$", r"\[x\)"])
def test_invalid_wrappers_and_empty_input(source):
    with pytest.raises(MathInputError):
        normalize_latex(source)


@pytest.mark.parametrize("source,expected", [
    (r"\frac{1}{3}+\frac{1}{6}", Rational(1, 2)),
    ("0.1+0.2", Rational(3, 10)),
    ("x+x", 2 * Symbol("x")),
    ("x_1+x_1", 2 * Symbol("x_1")),
    ("(x+1)^2", (Symbol("x") + 1) ** 2),
])
def test_exact_scalar_parsing(source, expected):
    parsed = parse_expression(source)
    assert simplify(parsed.expression - expected) == 0


@pytest.mark.parametrize("source", ["x+", "(", r"\frac{1}{", "x)junk"])
def test_invalid_latex_does_not_silently_parse_a_prefix(source):
    with pytest.raises(MathInputError) as error:
        parse_expression(source)
    assert error.value.status is PreparationStatus.ERROR


@pytest.mark.parametrize("source", [
    "x^2-2=0", r"\sin(x)", r"\log(10)", r"\int x dx", r"\frac{d}{dx}x^2", "x^{1/2}", "0^0",
])
def test_capability_check_precedes_unsafe_conversion(source):
    with pytest.raises(MathInputError) as error:
        parse_expression(source)
    assert error.value.status is PreparationStatus.UNSUPPORTED


def test_denominator_constraint_survives_parsing():
    parsed = parse_expression("x/x")
    assert simplify(parsed.expression) == 1
    assert len(parsed.conditions) == 1
    assert parsed.conditions[0].lhs == Symbol("x")


def test_nested_power_does_not_erase_original_denominator_constraint():
    parsed = parse_expression("(x/x)^0")
    assert simplify(parsed.expression) == 1
    assert parsed.conditions[0].lhs == Symbol("x")
