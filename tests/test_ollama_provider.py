"""测试 Ollama Provider 的请求和响应转换。"""

# 导入类型工具。
from typing import Any

# 导入 pytest，用于验证异常。
import pytest

# 导入消息类型。
from code_harness.core.messages import Message, Role, ToolCall, ToolCallFunction

# 导入供应商和异常。
from code_harness.providers.base import ProviderError
from code_harness.providers.ollama import OllamaProvider


class FakeResponse:
    """模拟 requests 响应对象。"""

    def __init__(self, data: dict[str, Any], status_code: int = 200) -> None:
        """保存响应数据。"""

        # 保存 JSON 数据。
        self.data = data

        # 保存状态码。
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """模拟 HTTP 状态检查。"""

        # 非 2xx 状态码时模拟 requests 异常。
        if self.status_code >= 400:
            raise __import__("requests").HTTPError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, Any]:
        """返回模拟 JSON。"""

        # 直接返回保存的数据。
        return self.data


class FakeSession:
    """模拟 requests.Session。"""

    def __init__(self, response: FakeResponse) -> None:
        """保存下一次请求要返回的响应。"""

        # 保存响应。
        self.response = response

        # 记录请求参数，便于测试验证。
        self.last_call: dict[str, Any] = {}

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        """模拟 POST 请求。"""

        # 保存地址和参数。
        self.last_call = {"method": "POST", "url": url, **kwargs}

        # 返回模拟响应。
        return self.response

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        """模拟 GET 请求。"""

        # 保存地址和参数。
        self.last_call = {"method": "GET", "url": url, **kwargs}

        # 返回模拟响应。
        return self.response

    def close(self) -> None:
        """模拟关闭连接。"""

        # 测试中不需要额外操作。
        return None


def test_chat_returns_assistant_message() -> None:
    """普通聊天应返回助手消息。"""

    # 创建包含回答的假响应。
    session = FakeSession(FakeResponse({"message": {"role": "assistant", "content": "ok"}}))

    # 创建 Provider。
    provider = OllamaProvider(base_url="http://localhost:11434", model="test-model", session=session)

    # 执行聊天。
    message = provider.chat([Message.user("你好")], temperature=0.2)

    # 验证返回消息。
    assert message.role is Role.ASSISTANT
    assert message.content == "ok"

    # 验证请求地址和参数。
    assert session.last_call["url"] == "http://localhost:11434/api/chat"
    assert session.last_call["json"]["model"] == "test-model"
    assert session.last_call["json"]["options"] == {"temperature": 0.2}


def test_chat_parses_tool_calls() -> None:
    """工具调用响应应转换成内部 ToolCall。"""

    # 创建包含工具调用的假响应。
    session = FakeSession(
        FakeResponse(
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "calculator",
                                "arguments": '{"expression": "2+3"}',
                            },
                        }
                    ],
                }
            }
        )
    )

    # 创建 Provider 并执行聊天。
    provider = OllamaProvider(session=session)
    message = provider.chat([Message.user("计算 2+3")])

    # 验证工具调用。
    assert len(message.tool_calls) == 1
    assert message.tool_calls[0].function.arguments == {"expression": "2+3"}


def test_chat_requires_message_field() -> None:
    """缺少 message 字段时应报告协议错误。"""

    # 创建错误响应。
    session = FakeSession(FakeResponse({"done": True}))

    # 创建 Provider。
    provider = OllamaProvider(session=session)

    # 验证异常。
    with pytest.raises(ProviderError, match="缺少 message"):
        provider.chat([Message.user("你好")])


def test_health_and_list_models() -> None:
    """健康检查和模型列表应返回 Ollama 数据。"""

    # 创建模型列表响应。
    session = FakeSession(FakeResponse({"models": [{"name": "qwen2.5:7b"}]}))

    # 创建 Provider。
    provider = OllamaProvider(session=session)

    # 模型列表应正确解析。
    assert provider.list_models() == ["qwen2.5:7b"]

    # 健康检查应返回原始数据。
    assert "models" in provider.health()

def test_ollama_converts_native_tool_message_format() -> None:
    """发送工具历史时应使用 Ollama 原生格式。"""

    # 创建最终回答响应。
    session = FakeSession(FakeResponse({"message": {"role": "assistant", "content": "done"}}))

    # 创建助手工具调用消息。
    assistant_message = Message.assistant(
        tool_calls=[
            ToolCall(
                id="call-1",
                function=ToolCallFunction(name="calculator", arguments={"expression": "1+1"}),
            )
        ]
    )

    # 创建工具结果消息。
    tool_message = Message.tool_result("call-1", "2", name="calculator")

    # 创建 Provider 并发送历史。
    provider = OllamaProvider(session=session)
    provider.chat([assistant_message, tool_message])

    # 读取实际发送给 Ollama 的消息。
    sent_messages = session.last_call["json"]["messages"]

    # Ollama 原生接口要求 arguments 是对象。
    assert sent_messages[0]["tool_calls"][0]["function"]["arguments"] == {"expression": "1+1"}

    # 工具结果应使用 tool_name，而不是 OpenAI 的 name/tool_call_id。
    assert sent_messages[1]["tool_name"] == "calculator"
    assert "name" not in sent_messages[1]
    assert "tool_call_id" not in sent_messages[1]
