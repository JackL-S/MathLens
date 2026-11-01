"""仅验证契约表达力和文档示例，不代表 codec 或数学后端已实现。"""

import importlib
import inspect
import json
import pkgutil
from dataclasses import FrozenInstanceError, asdict, is_dataclass
from pathlib import Path
from typing import get_args, get_type_hints

import pytest

from mathlens import schemas
from mathlens.enums import (
    Completeness, DiagnosticCode, MessageType, PreparationStatus,
    ProcessingStage, ResultKind, Status,
)
from mathlens.schemas import (
    ComputeRequest, ComputeResponse, Diagnostic, DifferentiationTarget, DifferentiateSpec,
    ExpressionValue, FiniteSetValue, InputChoice, InputRequest, IntegrateSpec,
    IntegrationLimit, LatexInput, MathExpression, PreparationResponse,
    PreparedProblem, ResultPreferences, SolveSpec,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "docs" / "examples"


def representation(model):
    """只检查 JSON 表示，不代替将来 codec 的类型恢复和输入校验。"""
    return json.loads(json.dumps(asdict(model), ensure_ascii=False, allow_nan=False))


def example(name):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def prepared_equation(latex="x^2-2=0"):
    return PreparedProblem(
        original_input=LatexInput(latex=latex),
        latex=latex,
        operation=SolveSpec(unknowns=("x",)),
        symbols=(),
        preferences=ResultPreferences(),
    )


def test_documented_differentiation_request():
    request = ComputeRequest(
        input=LatexInput(latex="x^3"),
        operation=DifferentiateSpec(
            targets=(DifferentiationTarget(variable="x", order=2),),
        ),
    )
    assert representation(request) == example("differentiate-request.json")


def test_documented_exact_solution():
    response = ComputeResponse(
        status=Status.SUCCESS,
        problem=prepared_equation(),
        result_kind=ResultKind.EXACT,
        completeness=Completeness.COMPLETE,
        value=FiniteSetValue(elements=(
            ExpressionValue(expression=MathExpression(
                latex=r"-\sqrt{2}", text="-sqrt(2)",
            )),
            ExpressionValue(expression=MathExpression(
                latex=r"\sqrt{2}", text="sqrt(2)",
            )),
        )),
        latex=r"x \in \{-\sqrt{2}, \sqrt{2}\}",
    )
    assert representation(response) == example("solve-response.json")


def test_documented_variable_confirmation():
    response = PreparationResponse(
        status=PreparationStatus.NEEDS_INPUT,
        preview=MathExpression(latex="x y", text="x*y"),
        input_requests=(InputRequest(
            code=DiagnosticCode.MISSING_VARIABLE,
            message="请选择求导变量",
            field_path="/operation/targets",
            choices=tuple(
                InputChoice(
                    choice_id=name,
                    label=name,
                    operation=DifferentiateSpec(
                        targets=(DifferentiationTarget(variable=name),),
                    ),
                )
                for name in ("x", "y")
            ),
        ),),
    )
    assert representation(response) == example("needs-input-response.json")


def test_empty_set_is_distinct_from_no_result():
    empty = ComputeResponse(
        status=Status.SUCCESS,
        problem=prepared_equation("x^2+1=0"),
        result_kind=ResultKind.EXACT,
        completeness=Completeness.COMPLETE,
        value=FiniteSetValue(elements=()),
        latex=r"\varnothing",
    )
    failure = ComputeResponse(status=Status.ERROR)
    assert representation(empty)["value"] == {"kind": "finite_set", "elements": []}
    assert representation(failure)["value"] is None
    assert representation(failure)["result_kind"] == "none"


def test_exact_decimal_in_integration_bound_is_preserved():
    decimal = "0.12345678901234567890123456789"
    request = ComputeRequest(
        input=LatexInput(latex="x"),
        operation=IntegrateSpec(limits=(IntegrationLimit(
            variable="x", lower=decimal, upper="1",
        ),)),
    )
    assert representation(request)["operation"]["limits"][0]["lower"] == decimal


def test_prepared_snapshot_cannot_be_rewritten_in_place():
    problem = prepared_equation()
    with pytest.raises(FrozenInstanceError):
        problem.latex = "x=1"


@pytest.mark.parametrize("union", [
    schemas.InputSpec, schemas.OperationSpec, schemas.MathValue,
    schemas.WorkerTask, schemas.WorkerResponse,
])
def test_tagged_unions_have_unambiguous_tags(union):
    tags = [model.__dataclass_fields__["kind"].default for model in get_args(union)]
    assert len(tags) == len(set(tags))


def test_all_nested_contract_annotations_resolve():
    for model in vars(schemas).values():
        if inspect.isclass(model) and is_dataclass(model):
            get_type_hints(model)


def test_diagnostic_code_has_a_stable_json_string():
    diagnostic = Diagnostic(
        code=DiagnosticCode.INVALID_IMAGE,
        message="图片无法解码",
        severity=MessageType.ERROR,
        stage=ProcessingStage.INPUT,
    )
    assert representation(diagnostic)["code"] == "invalid_image"


def test_unknown_diagnostic_code_can_be_preserved():
    diagnostic = Diagnostic(
        code="future_diagnostic_code",
        message="未来版本的诊断",
        severity=MessageType.WARNING,
        stage=ProcessingStage.COMPUTE,
    )
    assert representation(diagnostic)["code"] == "future_diagnostic_code"


def test_schema_models_have_a_canonical_public_export():
    assert len(schemas.__all__) == len(set(schemas.__all__))
    for exported_name in schemas.__all__:
        assert hasattr(schemas, exported_name)
    for info in pkgutil.iter_modules(schemas.__path__, schemas.__name__ + "."):
        module = importlib.import_module(info.name)
        for name, model in vars(module).items():
            if (
                inspect.isclass(model)
                and is_dataclass(model)
                and model.__module__ == module.__name__
            ):
                assert name in schemas.__all__
                assert getattr(schemas, name) is model


@pytest.mark.parametrize("module_name", [
    "application", "execution", "codec", "jobs", "media", "ocr",
    "rendering.formats", "cli",
])
def test_public_interface_annotations_resolve(module_name):
    module = importlib.import_module("mathlens." + module_name)
    for item in vars(module).values():
        if inspect.isfunction(item) and item.__module__ == module.__name__:
            get_type_hints(item)
