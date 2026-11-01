"""请求组合校验与执行选项的边界行为。"""

import pytest

from mathlens.application import prepare
from mathlens.enums import DiagnosticCode, MethodPolicy, PreparationStatus, ProcessingStage
from mathlens.schemas import (
    ComputeRequest, DifferentiationTarget, DifferentiateSpec, ExecutionOptions,
    ImageInput, ImageRegion, LatexInput, NumericOptions, ResourceLimits,
    ResultPreferences, SimplifySpec, SolveSpec, SymbolAssumptions, SymbolDeclaration,
)


def request(**changes):
    values = {"input": LatexInput(latex="x+x"), "operation": SimplifySpec()}
    values.update(changes)
    return ComputeRequest(**values)


@pytest.mark.parametrize("value,path", [
    (request(preferences={}), "/preferences"),
    (request(preferences=ResultPreferences(include_steps=1)), "/preferences/include_steps"),
    (request(preferences=ResultPreferences(significant_digits=True)), "/preferences/significant_digits"),
    (request(preferences=ResultPreferences(method="symbolic_first")), "/preferences/method"),
    (request(symbols=[]), "/symbols"),
    (request(symbols=(None,)), "/symbols/0"),
    (request(symbols=(SymbolDeclaration(name="x", assumptions={}),)), "/symbols/0/assumptions"),
    (request(input=ImageInput(media_id="")), "/input/media_id"),
    (request(input=ImageInput(media_id="image", region=ImageRegion(x=-1, y=0, width=1, height=1))),
     "/input/region/x"),
    (request(input=LatexInput(latex="x", source={})), "/input/source"),
])
def test_malformed_request_fields_return_diagnostics(value, path):
    response = prepare(value)
    assert response.status is PreparationStatus.ERROR
    assert any(path in item.field_paths for item in response.diagnostics)


def test_request_aggregates_independent_problems():
    response = prepare(request(operation=None, preferences=ResultPreferences(include_steps=1)))
    assert response.status is PreparationStatus.ERROR
    assert response.input_requests[0].code is DiagnosticCode.MISSING_OPERATION
    assert response.diagnostics[0].field_paths == ("/preferences/include_steps",)


@pytest.mark.parametrize("assumptions", [
    SymbolAssumptions(positive=True, real=False),
    SymbolAssumptions(integer=True, real=False),
    SymbolAssumptions(positive=True, nonzero=False),
    SymbolAssumptions(nonnegative=True, nonzero=True, positive=False),
])
def test_contradictory_assumptions_request_correction(assumptions):
    response = prepare(request(symbols=(SymbolDeclaration(name="x", assumptions=assumptions),)))
    assert response.status is PreparationStatus.NEEDS_INPUT
    assert all(item.code is DiagnosticCode.CONFLICTING_ARGUMENTS for item in response.input_requests)


def test_duplicate_symbols_are_invalid():
    response = prepare(request(symbols=(SymbolDeclaration(name="x"), SymbolDeclaration(name="x"))))
    assert response.status is PreparationStatus.ERROR
    assert response.diagnostics[0].field_paths == ("/symbols/1/name",)


def test_method_and_numeric_options_are_checked_together():
    response = prepare(request(
        operation=SolveSpec(unknowns=("x",), numeric=NumericOptions()),
        preferences=ResultPreferences(method=MethodPolicy.SYMBOLIC_ONLY),
    ))
    assert response.status is PreparationStatus.NEEDS_INPUT
    assert response.input_requests[0].field_path == "/operation/numeric"


@pytest.mark.parametrize("options,path", [
    ({}, ""),
    (ExecutionOptions(timeout_seconds=float("nan")), "/timeout_seconds"),
    (ExecutionOptions(timeout_seconds=float("inf")), "/timeout_seconds"),
    (ExecutionOptions(timeout_seconds=True), "/timeout_seconds"),
    (ExecutionOptions(cleanup_timeout_seconds=0), "/cleanup_timeout_seconds"),
    (ExecutionOptions(allow_partial_result=1), "/allow_partial_result"),
    (ExecutionOptions(limits={}), "/limits"),
    (ExecutionOptions(limits=ResourceLimits(max_input_bytes=0)), "/limits/max_input_bytes"),
])
def test_invalid_execution_configuration_has_execution_diagnostics(options, path):
    response = prepare(request(), options=options)
    assert response.status is PreparationStatus.ERROR
    assert any(item.field_paths == (path,) for item in response.diagnostics)
    assert all(item.stage is ProcessingStage.EXECUTION for item in response.diagnostics)


def test_byte_limit_uses_utf8_size():
    response = prepare(request(input=LatexInput(latex="中")), options=ExecutionOptions(
        limits=ResourceLimits(max_input_bytes=2),
    ))
    assert response.status is PreparationStatus.ERROR
    assert response.diagnostics[0].code is DiagnosticCode.RESOURCE_LIMIT_EXCEEDED


def test_derivative_limit_is_a_runtime_policy_not_spec_validity():
    operation = DifferentiateSpec(targets=(DifferentiationTarget(variable="x", order=4),))
    assert operation.validate() == ()
    response = prepare(request(operation=operation), options=ExecutionOptions(
        limits=ResourceLimits(max_derivative_order=3),
    ))
    assert response.status is PreparationStatus.ERROR
    assert response.diagnostics[0].code is DiagnosticCode.RESOURCE_LIMIT_EXCEEDED
    assert response.diagnostics[0].field_paths == ("/operation/targets/0/order",)


def test_unicode_encoding_problem_does_not_escape_prepare():
    response = prepare(request(input=LatexInput(latex="\ud800")))
    assert response.status is PreparationStatus.ERROR
    assert response.diagnostics[0].code is DiagnosticCode.INVALID_LATEX
