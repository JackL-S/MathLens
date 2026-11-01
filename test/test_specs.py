"""Spec 自身规则：构造允许不完整参数，显式校验返回问题而非抛异常。"""

import pytest

from mathlens.enums import DiagnosticCode, ValidationIssueKind
from mathlens.schemas import (
    DifferentiationTarget, DifferentiateSpec, EvaluateSpec, IntegrateSpec,
    IntegrationLimit, LimitSpec, NumericOptions, SearchInterval, SimplifySpec,
    SolveSpec, Substitution,
)


@pytest.mark.parametrize("spec", [
    SimplifySpec(),
    EvaluateSpec(),
    EvaluateSpec(substitutions=(Substitution(variable="x", value="1/3"),)),
    DifferentiateSpec(targets=(DifferentiationTarget(variable="x", order=2),)),
    DifferentiateSpec(targets=(
        DifferentiationTarget(variable="x"), DifferentiationTarget(variable="x"),
    )),
    IntegrateSpec(limits=(IntegrationLimit(variable="x"),)),
    IntegrateSpec(limits=(IntegrationLimit(variable="x", lower="1", upper="0"),)),
    SolveSpec(unknowns=("x",)),
    SolveSpec(unknowns=("x",), numeric=NumericOptions(
        search_intervals=(SearchInterval(variable="x", lower="0", upper="1"),),
    )),
    LimitSpec(variable="x", point="0"),
])
def test_valid_parameters_do_not_produce_issues(spec):
    assert spec.validate() == ()


@pytest.mark.parametrize("spec,path,code", [
    (DifferentiateSpec(), "/targets", DiagnosticCode.MISSING_VARIABLE),
    (IntegrateSpec(), "/limits", DiagnosticCode.MISSING_VARIABLE),
    (SolveSpec(), "/unknowns", DiagnosticCode.MISSING_VARIABLE),
    (LimitSpec(point="0"), "/variable", DiagnosticCode.MISSING_VARIABLE),
    (LimitSpec(variable="x"), "/point", DiagnosticCode.MISSING_FIELD),
    (IntegrateSpec(limits=(IntegrationLimit(variable="x", lower="0"),)),
     "/limits/0/upper", DiagnosticCode.MISSING_BOUND),
    (IntegrateSpec(limits=(IntegrationLimit(variable="x", upper="1"),)),
     "/limits/0/lower", DiagnosticCode.MISSING_BOUND),
])
def test_missing_parameters_are_actionable(spec, path, code):
    issues = spec.validate()
    assert len(issues) == 1
    assert issues[0].kind is ValidationIssueKind.MISSING
    assert issues[0].code is code
    assert issues[0].field_path == path


@pytest.mark.parametrize("order", [0, -1, True, "2", None])
def test_invalid_derivative_order_returns_issue(order):
    target = DifferentiationTarget(variable="x", order=order)
    issues = target.validate()
    assert len(issues) == 1
    assert issues[0].kind is ValidationIssueKind.INVALID
    assert issues[0].field_path == "/order"


@pytest.mark.parametrize("spec,path", [
    (DifferentiateSpec(targets=None), "/targets"),
    (DifferentiateSpec(targets=[]), "/targets"),
    (DifferentiateSpec(targets=(None,)), "/targets/0"),
    (IntegrateSpec(limits=(None,)), "/limits/0"),
    (IntegrateSpec(limits=(IntegrationLimit(variable="x", lower=0, upper="1"),)),
     "/limits/0/lower"),
    (SolveSpec(unknowns=([],)), "/unknowns/0"),
    (SolveSpec(unknowns=("x",), solution_domain="real"), "/solution_domain"),
    (SolveSpec(unknowns=("x",), numeric={}), "/numeric"),
    (LimitSpec(variable="x", point="0", direction="both"), "/direction"),
    (EvaluateSpec(substitutions=(Substitution(variable="x", value=1),)),
     "/substitutions/0/value"),
    (SolveSpec(unknowns=("x",), numeric=NumericOptions(significant_digits=True)),
     "/numeric/significant_digits"),
])
def test_malformed_nested_parameters_do_not_raise(spec, path):
    issues = spec.validate()
    assert any(
        issue.kind is ValidationIssueKind.INVALID and issue.field_path == path
        for issue in issues
    )


@pytest.mark.parametrize("spec,path", [
    (SolveSpec(unknowns=("x", "x")), "/unknowns/1"),
    (EvaluateSpec(substitutions=(
        Substitution(variable="x", value="1"), Substitution(variable="x", value="2"),
    )), "/substitutions/1/variable"),
    (SolveSpec(unknowns=("x",), numeric=NumericOptions(initial_values=(
        Substitution(variable="x", value="1"), Substitution(variable="x", value="2"),
    ))), "/numeric/initial_values/1/variable"),
])
def test_duplicate_assignments_and_unknowns_are_rejected(spec, path):
    assert any(issue.field_path == path for issue in spec.validate())


def test_numeric_variable_must_belong_to_unknowns():
    spec = SolveSpec(unknowns=("x",), numeric=NumericOptions(
        initial_values=(Substitution(variable="y", value="1"),),
    ))
    issues = spec.validate()
    assert len(issues) == 1
    assert issues[0].kind is ValidationIssueKind.CONFLICT
    assert issues[0].code is DiagnosticCode.CONFLICTING_ARGUMENTS
    assert issues[0].field_path == "/numeric/initial_values/0/variable"


def test_unrelated_invalid_domain_does_not_hide_numeric_conflict():
    spec = SolveSpec(unknowns=("x",), solution_domain="invalid", numeric=NumericOptions(
        initial_values=(Substitution(variable="y", value="1"),),
    ))
    issues = spec.validate()
    assert {issue.field_path for issue in issues} == {
        "/solution_domain", "/numeric/initial_values/0/variable",
    }


def test_multiple_issues_are_preserved_and_prefixing_does_not_mutate():
    spec = DifferentiateSpec(targets=(DifferentiationTarget(variable="", order=0),))
    issues = spec.validate()
    assert {issue.kind for issue in issues} == {
        ValidationIssueKind.MISSING, ValidationIssueKind.INVALID,
    }
    assert issues[0].prefixed("/operation").field_path == "/operation/targets/0/variable"
    assert issues[0].field_path == "/targets/0/variable"
