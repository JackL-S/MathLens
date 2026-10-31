"""图片资源生命周期接口；计算模块不读取用户路径。"""

from .schemas import MediaResource, ResourceLimits


def register_media(
    data: bytes,
    *,
    media_type: str,
    limits: ResourceLimits | None = None,
) -> MediaResource:
    """校验字节大小、真实图像格式和像素数，注册不透明资源标识。

    路径、URL 和上传方式由入口处理。格式或容量错误抛 ValueError；
    I/O 失败抛 OSError，应用边界转换为 input 阶段诊断。
    """
    raise NotImplementedError


def release_media(media_id: str) -> None:
    """释放调用方持有的资源；任务引用存续期间不得提前销毁内容。

    重复释放同一已知标识应幂等；未知标识抛 ValueError。
    """
    raise NotImplementedError
