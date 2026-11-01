from mathlens.pipeline import process_task
from mathlens.enums import ResultKind, Status, StepsStatus
from mathlens.schemas import ComputeRequest, ExecutionOptions, LatexInput, ResultPreferences, RunTask, SimplifySpec


def test_run_core_keeps_exact_value_conditions_and_independent_steps():
    response = process_task(RunTask(request=ComputeRequest(
        input=LatexInput(latex="x/x"), operation=SimplifySpec(),
        preferences=ResultPreferences(include_steps=True),
    )), ExecutionOptions())
    assert response.status is Status.SUCCESS
    assert response.result_kind is ResultKind.EXACT
    assert response.value.expression.text == "1"
    assert response.conditions[0].expression.text == "Ne(x, 0)"
    assert response.steps.status is StepsStatus.UNAVAILABLE
