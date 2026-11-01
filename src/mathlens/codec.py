"""按现有 dataclass 契约恢复 JSON，规则见 docs/interfaces.md。

不能用 json.loads 后直接 ** 解包代替嵌套模型校验。解码器负责恢复
枚举、标签联合及 tuple，拒绝未知输入字段、非有限数值和错误版本。
"""

from dataclasses import fields, is_dataclass, replace
from enum import Enum
import json
from math import isfinite
from types import UnionType
from typing import Literal, TypeAlias, Union, get_args, get_origin, get_type_hints

from .enums import DiagnosticCode
from .schemas import Diagnostic, InputRequest, ResourceLimits

from .schemas import (
    ApplicationResponse, Capabilities, ComputeRequest, ExecutionOptions,
    PreparedProblem, WorkerRequest, WorkerResult,
)

PublicDocument: TypeAlias = (
    ComputeRequest | PreparedProblem | ApplicationResponse
    | ExecutionOptions | Capabilities
)


class ContractDecodeError(ValueError):
    """解码失败，应用边界将其转换为结构化诊断。

    code 使用 DiagnosticCode 的对应字符串；field_path 是 JSON Pointer，根为 ""。
    """

    code: str
    field_path: str

    def __init__(self, code: str, message: str, *, field_path: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.field_path = field_path



def _fail(path: str, message: str, code: str = "invalid_request"):
    raise ContractDecodeError(code, message, field_path=path)


def _restore(expected, value, path=""):
    origin = get_origin(expected)
    args = get_args(expected)
    if origin in (Union, UnionType):
        if value is None and type(None) in args:
            return None
        candidates = [item for item in args if item is not type(None)]
        if len(candidates) == 1:
            return _restore(candidates[0], value, path)
        if not isinstance(value, dict) or "kind" not in value:
            _fail(path, "联合模型缺少 kind")
        for candidate in candidates:
            hints = get_type_hints(candidate)
            labels = get_args(hints.get("kind"))
            if value["kind"] in labels:
                return _restore(candidate, value, path)
        _fail(path + "/kind", "未知模型标签")
    if origin is Literal:
        for item in args:
            if (isinstance(item, Enum) and type(value) is str and value == item.value):
                return item
            if type(value) is type(item) and value == item:
                return item
        _fail(path, "模型标签不正确")
    if origin is tuple:
        if not isinstance(value, list):
            _fail(path, "需要 JSON 数组")
        return tuple(_restore(args[0], item, f"{path}/{index}") for index, item in enumerate(value))
    if isinstance(expected, type) and issubclass(expected, Enum):
        if type(value) is not str:
            _fail(path, "枚举必须是字符串")
        try:
            return expected(value)
        except ValueError:
            _fail(path, "未知枚举值")
    if isinstance(expected, type) and is_dataclass(expected):
        if not isinstance(value, dict):
            _fail(path, "需要 JSON 对象")
        declared = {item.name: item for item in fields(expected)}
        if value.keys() - declared.keys():
            _fail(path, "存在未知字段")
        hints = get_type_hints(expected)
        kwargs = {}
        for name, item in declared.items():
            location = path + "/" + name
            if name == "schema_version" and (type(value.get(name)) is not int or value[name] != 1):
                _fail(location, "公开契约版本不正确", "schema_version_mismatch")
            if name == "protocol_version" and (type(value.get(name)) is not int or value[name] != 1):
                _fail(location, "通信协议版本不正确", "protocol_version_mismatch")
            if name in value:
                restored = _restore(hints[name], value[name], location)
                if item.init:
                    kwargs[name] = restored
            elif not item.init:
                _fail(location, "模型缺少标签")
        try:
            model = expected(**kwargs)
        except TypeError as exc:
            _fail(path, str(exc))
        if expected in (Diagnostic, InputRequest):
            try:
                model = replace(model, code=DiagnosticCode(model.code))
            except ValueError:
                pass
        return model
    if expected is float and type(value) in (int, float):
        try:
            return float(value)
        except OverflowError:
            _fail(path, "数值超出范围")
    if type(value) is not expected:
        _fail(path, "字段类型不正确")
    return value


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            _fail("", "JSON 存在重复键", "invalid_json")
        result[key] = value
    return result


def _read(payload: bytes):
    if len(payload) > ResourceLimits().max_output_bytes:
        _fail("", "JSON 超出默认容量", "resource_limit_exceeded")
    try:
        data = json.loads(payload.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=lambda value: _fail("", "禁止非有限数值", "invalid_json"))
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, ContractDecodeError):
            raise
        _fail("", "无效 JSON", "invalid_json")
    stack = [(data, 0)]
    while stack:
        value, depth = stack.pop()
        if depth > ResourceLimits().max_json_depth:
            _fail("", "JSON 嵌套过深", "resource_limit_exceeded")
        if isinstance(value, dict):
            stack.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            stack.extend((item, depth + 1) for item in value)
        elif isinstance(value, float):
            if not isfinite(value):
                _fail("", "禁止非有限数值", "invalid_json")
    return data


def _json_tree(value):
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _json_tree(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_json_tree(item) for item in value]
    return value


def _encode(document):
    tree = _json_tree(document)
    try:
        payload = json.dumps(tree, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        _fail("", f"结果不能编码为严格 JSON：{exc}", "serialization_failed")
    _restore(type(document), _read(payload))
    return payload


def decode_request(payload: bytes) -> ComputeRequest:
    return _restore(ComputeRequest, _read(payload))


def decode_prepared_problem(payload: bytes) -> PreparedProblem:
    return _restore(PreparedProblem, _read(payload))


def decode_response(payload: bytes) -> ApplicationResponse:
    return _restore(ApplicationResponse, _read(payload))


def encode_public(document: PublicDocument) -> bytes:
    if not isinstance(document, PublicDocument):
        _fail("", "需要公开文档模型")
    return _encode(document)


def decode_worker_request(payload: bytes) -> WorkerRequest:
    return _restore(WorkerRequest, _read(payload))


def decode_worker_result(payload: bytes) -> WorkerResult:
    return _restore(WorkerResult, _read(payload))


def encode_worker(document: WorkerRequest | WorkerResult) -> bytes:
    return _encode(document)
