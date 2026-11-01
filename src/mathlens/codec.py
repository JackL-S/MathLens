"""JSON 边界接口，规则见 docs/interfaces.md；此处不实现转换。

不能用 json.loads 后直接 ** 解包代替嵌套模型校验。解码器负责恢复
枚举、标签联合及 tuple，拒绝未知输入字段、非有限数值和错误版本。
"""

from typing import TypeAlias

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

    code 为 invalid_json / invalid_request / schema_version_mismatch /
    protocol_version_mismatch；field_path 是 JSON Pointer，根为 ""。
    """

    code: str
    field_path: str

    def __init__(self, code: str, message: str, *, field_path: str = "") -> None:
        """声明异常构造契约；与 codec 一同实现。"""
        raise NotImplementedError


def decode_request(payload: bytes) -> ComputeRequest:
    """校验 UTF-8 JSON 请求；失败抛 ContractDecodeError。"""
    raise NotImplementedError


def decode_prepared_problem(payload: bytes) -> PreparedProblem:
    """恢复快照并校验结构；compute 仍须检查数学与能力约束。"""
    raise NotImplementedError


def decode_response(payload: bytes) -> ApplicationResponse:
    """严格解码响应，通过 kind 区分模型；失败抛 ContractDecodeError。"""
    raise NotImplementedError


def encode_public(document: PublicDocument) -> bytes:
    """输出 UTF-8 严格 JSON；校验所有嵌套字段，不允许 NaN/Infinity。"""
    raise NotImplementedError


def decode_worker_request(payload: bytes) -> WorkerRequest:
    """校验 IPC envelope 及内层模型；失败抛 ContractDecodeError。"""
    raise NotImplementedError


def decode_worker_result(payload: bytes) -> WorkerResult:
    """恢复 IPC 响应；调用端另检查响应与原任务的类型匹配。"""
    raise NotImplementedError


def encode_worker(document: WorkerRequest | WorkerResult) -> bytes:
    """编码 IPC envelope，协议版本与公开 schema_version 独立。"""
    raise NotImplementedError
