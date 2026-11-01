import pytest

from mathlens.application import prepare
from mathlens.enums import DiagnosticCode, PreparationStatus
from mathlens.schemas import (
    ComputeRequest, DifferentiationTarget, DifferentiateSpec, IntegrateSpec,
    IntegrationLimit, LatexInput, LimitSpec, NumericOptions, SimplifySpec,
    SolveSpec, Substitution,
)


def test_prepare_rejects_non_string_latex():
    request = ComputeRequest(
        input=LatexInput(latex=123),
        operation=SimplifySpec(),
    )

    response = prepare(request)

    assert response.status is PreparationStatus.ERROR
    assert response.problem is None
    assert response.diagnostics[0].code is DiagnosticCode.INVALID_REQUEST
    assert response.diagnostics[0].field_paths == ("/input/latex",)


def test_prepare_rejects_blank_latex():
    response = prepare(ComputeRequest(
        input=LatexInput(latex="   "),
        operation=SimplifySpec(),
    ))

    assert response.status is PreparationStatus.ERROR
    assert response.diagnostics[0].code is DiagnosticCode.INVALID_LATEX


def test_prepare_rejects_invalid_input_structure():
    response = prepare(ComputeRequest(input=None))

    assert response.status is PreparationStatus.ERROR
    assert response.diagnostics[0].code is DiagnosticCode.INVALID_REQUEST
    assert response.diagnostics[0].field_paths == ("/input",)


def test_prepare_requests_missing_operation():
    response = prepare(ComputeRequest(input=LatexInput(latex="x+x")))

    assert response.status is PreparationStatus.NEEDS_INPUT
    assert response.input_requests[0].code is DiagnosticCode.MISSING_OPERATION
    assert response.input_requests[0].field_path == "/operation"


def test_prepare_converts_nested_missing_bound_to_input_request():
    response = prepare(ComputeRequest(
        input=LatexInput(latex="x"),
        operation=IntegrateSpec(limits=(IntegrationLimit(variable="x", lower="0"),)),
    ))
    assert response.status is PreparationStatus.NEEDS_INPUT
    assert response.input_requests[0].code is DiagnosticCode.MISSING_BOUND
    assert response.input_requests[0].field_path == "/operation/limits/0/upper"
    assert response.problem is None


def test_prepare_reports_invalid_and_missing_parameters_together():
    response = prepare(ComputeRequest(
        input=LatexInput(latex="x"),
        operation=DifferentiateSpec(targets=(DifferentiationTarget(variable="", order=0),)),
    ))
    assert response.status is PreparationStatus.ERROR
    assert response.diagnostics[0].code is DiagnosticCode.INVALID_REQUEST
    assert response.diagnostics[0].field_paths == ("/operation/targets/0/order",)
    assert response.input_requests[0].field_path == "/operation/targets/0/variable"
    assert response.problem is None


def test_prepare_collects_all_missing_limit_parameters():
    response = prepare(ComputeRequest(input=LatexInput(latex="x"), operation=LimitSpec()))
    assert response.status is PreparationStatus.NEEDS_INPUT
    assert {item.field_path for item in response.input_requests} == {
        "/operation/variable", "/operation/point",
    }


def test_prepare_reports_numeric_parameter_conflict_as_needs_input():
    response = prepare(ComputeRequest(
        input=LatexInput(latex="x^2-2=0"),
        operation=SolveSpec(unknowns=("x",), numeric=NumericOptions(
            initial_values=(Substitution(variable="y", value="1"),),
        )),
    ))
    assert response.status is PreparationStatus.NEEDS_INPUT
    assert response.input_requests[0].code is DiagnosticCode.CONFLICTING_ARGUMENTS
    assert response.input_requests[0].field_path == "/operation/numeric/initial_values/0/variable"


def test_prepare_does_not_claim_ready_before_parsing_is_available():
    response = prepare(ComputeRequest(
        input=LatexInput(latex="x+x"), operation=SimplifySpec(),
    ))
    assert response.status is PreparationStatus.UNSUPPORTED
    assert response.diagnostics[0].code is DiagnosticCode.CAPABILITY_UNAVAILABLE
    assert response.problem is None


@pytest.mark.parametrize("compute_request,code,path", [
    (None, DiagnosticCode.INVALID_REQUEST, ""),
    (ComputeRequest(input=LatexInput(latex="x"), schema_version=True),
     DiagnosticCode.SCHEMA_VERSION_MISMATCH, "/schema_version"),
    (ComputeRequest(input=LatexInput(latex="x"), schema_version="1"),
     DiagnosticCode.SCHEMA_VERSION_MISMATCH, "/schema_version"),
    (ComputeRequest(input=LatexInput(latex="x"), operation="simplify"),
     DiagnosticCode.INVALID_REQUEST, "/operation"),
])
def test_runtime_structure_checks_survive_typed_model_annotations(compute_request, code, path):
    response = prepare(compute_request)
    assert response.status is PreparationStatus.ERROR
    assert response.diagnostics[0].code is code
    assert response.diagnostics[0].field_paths == (path,)
