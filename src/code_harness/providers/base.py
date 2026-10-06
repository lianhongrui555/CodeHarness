"""模型供应商的统一接口。"""

# 导入抽象基类工具，用于强制子类实现聊天方法。
from abc import ABC, abstractmethod

# 导入类型工具。
from typing import Any

# 导入统一消息类型。
from code_harness.core.messages import Message


class ProviderError(RuntimeError):
    """表示模型供应商调用失败。"""


class BaseProvider(ABC):
    """所有模型供应商都必须遵守的接口。"""

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
    ) -> Message:
        """发送消息并返回助手消息。"""

        # 抽象方法只定义接口，具体实现由子类完成。
        raise NotImplementedError
