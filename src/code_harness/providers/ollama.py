"""本地 Ollama 模型供应商。"""

# 导入系统环境变量工具。
import os

# 导入类型工具。
from typing import Any

# 导入 requests，用于访问 Ollama HTTP API。
import requests

# 导入统一消息和工具调用类型。
from code_harness.core.messages import Message

# 导入供应商基类和异常类型。
from code_harness.providers.base import BaseProvider, ProviderError


class OllamaProvider(BaseProvider):
    """连接 Ollama 原生聊天接口的模型供应商。"""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
        session: requests.Session | None = None,
    ) -> None:
        """初始化 Ollama Provider。"""

        # 优先读取传入地址，否则读取环境变量，最后使用本机默认地址。
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")

        # 优先读取传入模型，否则读取环境变量，最后使用 qwen2.5:7b。
        self.model = model or os.getenv("OLLAMA_MODEL") or "qwen2.5:7b"

        # 保存请求超时时间。
        self.timeout = timeout

        # 允许测试注入假 Session，也允许真实运行时创建新 Session。
        self.session = session or requests.Session()

    def _url(self, path: str) -> str:
        """拼接 Ollama API 地址。"""

        # 保证地址只有一条斜杠。
        return f"{self.base_url}/{path.lstrip('/')}"

    def health(self) -> dict[str, Any]:
        """检查 Ollama 服务是否正常。"""

        # 使用 try 捕获网络错误。
        try:
            # 请求版本接口。
            response = self.session.get(self._url("/api/version"), timeout=10)
            # HTTP 错误时抛出异常。
            response.raise_for_status()
            # 返回 JSON 数据。
            return response.json()
        except (requests.RequestException, ValueError) as error:
            # 统一转换成供应商异常。
            raise ProviderError(f"无法连接 Ollama：{error}") from error

    def list_models(self) -> list[str]:
        """返回 Ollama 中可用的模型名称。"""

        # 使用 try 捕获网络和 JSON 错误。
        try:
            # 请求模型列表接口。
            response = self.session.get(self._url("/api/tags"), timeout=15)
            # HTTP 错误时抛出异常。
            response.raise_for_status()
            # 读取返回数据。
            data = response.json()
        except (requests.RequestException, ValueError) as error:
            # 统一转换成供应商异常。
            raise ProviderError(f"读取 Ollama 模型列表失败：{error}") from error

        # 提取模型名称并忽略缺少 name 的记录。
        return [str(item["name"]) for item in data.get("models", []) if item.get("name")]

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
    ) -> Message:
        """调用 Ollama 聊天接口并返回助手消息。"""

        # 准备请求正文。
        payload: dict[str, Any] = {
            # 指定使用的模型。
            "model": self.model,
            # 把内部消息转换成接口格式。
            "messages": [message.to_api_dict() for message in messages],
            # 第一版不使用流式输出，方便调试完整结果。
            "stream": False,
        }

        # 有工具时加入工具定义。
        if tools:
            # tools 必须符合 OpenAI Function Calling 结构。
            payload["tools"] = tools

        # 有温度参数时加入模型选项。
        if temperature is not None:
            # Ollama 的采样参数放在 options 中。
            payload["options"] = {"temperature": temperature}

        # 使用 try 捕获网络和解析错误。
        try:
            # 发送聊天请求。
            response = self.session.post(
                self._url("/api/chat"),
                json=payload,
                timeout=self.timeout,
            )
            # HTTP 错误时抛出异常。
            response.raise_for_status()
            # 解析返回 JSON。
            data = response.json()
        except requests.Timeout as error:
            # 明确处理超时。
            raise ProviderError(f"Ollama 请求超时，模型：{self.model}") from error
        except requests.RequestException as error:
            # 处理其他网络错误。
            raise ProviderError(f"Ollama 请求失败：{error}") from error
        except ValueError as error:
            # 处理无效 JSON。
            raise ProviderError(f"Ollama 返回了无效 JSON：{error}") from error

        # 读取消息字段。
        message_data = data.get("message")

        # 缺少 message 字段时视为上游协议错误。
        if not isinstance(message_data, dict):
            raise ProviderError(f"Ollama 返回中缺少 message 字段：{data}")

        # 转换成内部统一消息对象。
        return Message.from_api_dict(message_data)

    def close(self) -> None:
        """关闭 HTTP Session。"""

        # 释放连接资源。
        self.session.close()
