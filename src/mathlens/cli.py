"""命令行入口契约，尚未注册可执行命令。"""

from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """调用应用接口，JSON 模式 stdout 只输出一个公开结果对象。

    日志写 stderr；计算 success 或仅准备 ready 返回 0，其他返回 1。
    输入错误也输出结构化响应；不直接调用解析器或求解器。
    """
    raise NotImplementedError
