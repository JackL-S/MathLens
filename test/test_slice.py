"""公开 API 的纵向切片，真实使用 spawn worker 和 JSON 通道。"""

from dataclasses import replace

import pytest

from mathlens.application import compute, get_capabilities, prepare, run
from mathlens.codec import decode_response, encode_public
from mathlens.enums import DiagnosticCode, Operation, PreparationStatus, Status
from mathlens.schemas import ComputeRequest, LatexInput, SimplifySpec


def request(latex):
    return ComputeRequest(input=LatexInput(latex=latex), operation=SimplifySpec())


@pytest.mark.parametrize("latex,expected", [
    ("x+x", "2*x"), (r"\frac{1}{3}+\frac{1}{6}", "1/2"),
    ("0.1+0.2", "3/10"), (r"$\frac{x^2-1}{x-1}$", "x + 1"),
])
def test_run_produces_public_exact_result(latex, expected):
    result = run(request(latex))
    assert result.status is Status.SUCCESS
    assert result.value.expression.text == expected
    assert result == decode_response(encode_public(result))


def test_separate_prepare_compute_and_tampered_snapshot():
    prepared = prepare(request("  x+x  "))
    assert prepared.status is PreparationStatus.READY
    assert prepared.problem.original_input.latex == "  x+x  "
    assert prepared.problem.changes
    result = compute(prepared.problem)
    assert result.status is Status.SUCCESS
    assert result.value.expression.text == "2*x"
    tampered = compute(replace(prepared.problem, latex="x+100"))
    assert tampered.status is Status.ERROR
    assert tampered.diagnostics[0].code is DiagnosticCode.INVALID_REQUEST


def test_rational_simplification_keeps_original_excluded_point():
    result = run(request(r"\frac{x^2-1}{x-1}"))
    assert result.status is Status.SUCCESS
    assert result.conditions[0].expression.text == "Ne(x - 1, 0)"
    assert result.conditions[0].expression.latex in result.latex


def test_invalid_latex_is_a_preparation_failure():
    result = run(request("x+"))
    assert result.status is PreparationStatus.ERROR
    assert result.diagnostics[0].code is DiagnosticCode.INVALID_LATEX


def test_capabilities_only_advertise_the_enabled_slice():
    capabilities = get_capabilities()
    assert [item.operation for item in capabilities.operations] == [Operation.SIMPLIFY]
    assert not capabilities.supports_assumptions
