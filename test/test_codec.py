from dataclasses import replace
import json

import pytest

from mathlens.codec import (
    ContractDecodeError, decode_prepared_problem, decode_request,
    decode_response, decode_worker_request, encode_public, encode_worker,
)
from mathlens.enums import DiagnosticCode, MessageType, ProcessingStage, Status
from mathlens.schemas import (
    ComputeRequest, ComputeResponse, Diagnostic, ExecutionOptions, LatexInput,
    PrepareTask, PreparedProblem, ResultPreferences, SimplifySpec, WorkerRequest,
)


def request():
    return ComputeRequest(input=LatexInput(latex="x+x"), operation=SimplifySpec())


def test_request_and_ipc_round_trip_restore_nested_models():
    value = request()
    assert decode_request(encode_public(value)) == value
    envelope = WorkerRequest(task=PrepareTask(request=value), options=ExecutionOptions())
    restored = decode_worker_request(encode_worker(envelope))
    assert restored == envelope
    assert isinstance(restored.task.request.operation, SimplifySpec)


def test_snapshot_round_trip():
    value = PreparedProblem(
        original_input=request().input, latex="x+x", operation=SimplifySpec(),
        symbols=(), preferences=ResultPreferences(),
    )
    assert decode_prepared_problem(encode_public(value)) == value


@pytest.mark.parametrize("field,value,expected", [
    ("schema_version", True, "schema_version_mismatch"),
    ("schema_version", "1", "schema_version_mismatch"),
    ("schema_version", 2, "schema_version_mismatch"),
    ("unknown", 1, "invalid_request"),
    ("operation", {"kind": "unknown"}, "invalid_request"),
])
def test_invalid_request_structure_is_rejected(field, value, expected):
    data = json.loads(encode_public(request()))
    data[field] = value
    with pytest.raises(ContractDecodeError) as error:
        decode_request(json.dumps(data).encode())
    assert error.value.code == expected


def test_missing_schema_version_is_not_filled_by_constructor_default():
    data = json.loads(encode_public(request()))
    del data["schema_version"]
    with pytest.raises(ContractDecodeError) as error:
        decode_request(json.dumps(data).encode())
    assert error.value.code == "schema_version_mismatch"


@pytest.mark.parametrize("payload", [
    b'{"x":1,"x":2}', b'NaN', b'Infinity', b'1e400', b'\xff', b'{',
])
def test_nonstandard_or_invalid_json_is_rejected(payload):
    with pytest.raises(ContractDecodeError) as error:
        decode_request(payload)
    assert error.value.code == "invalid_json"


def test_future_diagnostic_code_is_preserved_and_known_code_restored():
    diagnostic = Diagnostic(
        code=DiagnosticCode.INVALID_IMAGE, message="示例",
        severity=MessageType.ERROR, stage=ProcessingStage.INPUT,
    )
    known = decode_response(encode_public(ComputeResponse(status=Status.ERROR, diagnostics=(diagnostic,))))
    assert known.diagnostics[0].code is DiagnosticCode.INVALID_IMAGE
    unknown = decode_response(encode_public(ComputeResponse(
        status=Status.ERROR, diagnostics=(replace(diagnostic, code="future_code"),),
    )))
    assert unknown.diagnostics[0].code == "future_code"
