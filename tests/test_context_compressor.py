"""测试上下文压缩器。"""

# 导入消息类型。
from code_harness.core.messages import Message, Role, ToolCall, ToolCallFunction
from code_harness.context.compressor import ContextCompressor


class FakeSummaryProvider:
    """返回固定摘要的假模型。"""

    def __init__(self) -> None:
        """初始化调用记录。"""

        # 保存调用参数。
        self.calls = []

    def chat(self, messages, tools=None, temperature=None):
        """返回固定摘要。"""

        # 记录本次调用。
        self.calls.append({"messages": messages, "tools": tools, "temperature": temperature})

        # 返回摘要消息。
        return Message.assistant("用户正在开发 CodeHarness，并已完成会话保存。")


def test_compressor_skips_short_context() -> None:
    """上下文未超限时不应调用模型。"""

    # 创建假模型和压缩器。
    provider = FakeSummaryProvider()
    compressor = ContextCompressor(provider, max_tokens=100)

    # 创建短消息列表。
    messages = [Message.system("系统"), Message.user("短消息")]

    # 执行压缩。
    result = compressor.compress(messages)

    # 应返回原列表且不调用模型。
    assert result is messages
    assert provider.calls == []


def test_compressor_summarizes_old_messages_and_keeps_recent() -> None:
    """压缩后应保留系统提示和最近消息。"""

    # 创建假模型和压缩器。
    provider = FakeSummaryProvider()
    compressor = ContextCompressor(provider, max_tokens=20, keep_recent_messages=2)

    # 创建较长历史。
    messages = [
        Message.system("系统规则"),
        Message.user("旧任务" * 20),
        Message.assistant("旧回答" * 20),
        Message.user("最近问题"),
        Message.assistant("最近回答"),
    ]

    # 执行压缩。
    result = compressor.compress(messages)

    # 验证系统和最近消息保留。
    assert result[0].content == "系统规则"
    assert "压缩摘要" in result[1].content
    assert result[-2].content == "最近问题"
    assert result[-1].content == "最近回答"

    # 摘要调用不应传工具。
    assert provider.calls[0]["tools"] is None


def test_compressor_keeps_tool_call_pair_together() -> None:
    """最近消息从工具结果开始时，应向前保留对应工具调用。"""

    # 创建假模型和压缩器。
    provider = FakeSummaryProvider()
    compressor = ContextCompressor(provider, max_tokens=10, keep_recent_messages=2)

    # 创建包含工具结果的历史。
    messages = [
        Message.system("系统"),
        Message.user("算数" * 20),
        Message.assistant("准备工具" * 20),
        Message.assistant(tool_calls=[ToolCall(id="call-1", function=ToolCallFunction(name="calculator", arguments={"expression": "6*7"}))]),
        Message.tool_result("call-1", "42", name="calculator"),
        Message.assistant("结果是 42"),
    ]

    # 执行压缩。
    result = compressor.compress(messages)

    # 找到工具结果位置。
    tool_index = next(index for index, message in enumerate(result) if message.role is Role.TOOL)

    # 工具结果前面必须仍有助手工具调用消息。
    assert any(message.tool_calls for message in result[:tool_index])
