from mathlens.application import prepare
from mathlens.enums import DiagnosticCode, PreparationStatus
from mathlens.schemas import ComputeRequest, LatexInput, SimplifySpec


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
