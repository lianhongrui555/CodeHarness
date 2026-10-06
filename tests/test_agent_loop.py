"""测试 Agent Loop。"""

# 导入消息和工具类型。
from code_harness.core.messages import Message, ToolCall, ToolCallFunction
from code_harness.core.events import EventType
from code_harness.agent.loop import AgentLoop
from code_harness.tools.calculator import CalculatorTool
from code_harness.tools.registry import ToolRegistry


class FakeProvider:
    """按预设顺序返回模型响应。"""

    def __init__(self, responses: list[Message]) -> None:
        """保存响应列表。"""

        # 复制响应，避免测试之间互相影响。
        self.responses = list(responses)

        # 记录每轮收到的消息。
        self.calls: list[list[Message]] = []

    def chat(self, messages, tools=None, temperature=None):
        """返回下一条预设响应。"""

        # 保存当前消息历史副本。
        self.calls.append(list(messages))

        # 没有响应时抛出明确错误。
        if not self.responses:
            raise AssertionError("FakeProvider 没有剩余响应")

        # 返回下一条响应。
        return self.responses.pop(0)


def make_registry() -> ToolRegistry:
    """创建带计算器的工具注册表。"""

    # 创建注册表。
    registry = ToolRegistry()

    # 注册安全计算器。
    registry.register(CalculatorTool())

    # 返回注册表。
    return registry


def test_loop_returns_direct_answer() -> None:
    """模型不调用工具时应直接结束。"""

    # 创建只返回普通回答的假模型。
    provider = FakeProvider([Message.assistant("这是一个普通回答")])

    # 收集事件。
    events = []

    # 创建 Agent Loop。
    loop = AgentLoop(provider, make_registry(), event_sink=events.append)

    # 执行任务。
    result = loop.run("请简单介绍自己")

    # 验证结果。
    assert result.finished is True
    assert result.steps == 1
    assert result.final_content == "这是一个普通回答"
    assert [event.type for event in events] == [
        EventType.RUN_STARTED,
        EventType.ASSISTANT_MESSAGE,
        EventType.RUN_FINISHED,
    ]


def test_loop_executes_tool_and_returns_final_answer() -> None:
    """Agent 应执行工具并把结果发回模型。"""

    # 创建工具调用。
    tool_call = ToolCall(
        id="call-1",
        function=ToolCallFunction(name="calculator", arguments={"expression": "12345*6789"}),
    )

    # 第一轮返回工具调用，第二轮返回最终回答。
    provider = FakeProvider(
        [
            Message.assistant(tool_calls=[tool_call]),
            Message.assistant("计算结果是 83810205"),
        ]
    )

    # 收集事件。
    events = []

    # 创建 Agent Loop。
    loop = AgentLoop(provider, make_registry(), event_sink=events.append)

    # 执行任务。
    result = loop.run("请计算 12345*6789")

    # 验证结果。
    assert result.finished is True
    assert result.steps == 2
    assert result.final_content == "计算结果是 83810205"

    # 验证工具结果被写入历史。
    tool_messages = [message for message in result.messages if message.role.value == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0].content == "83810205"
    assert tool_messages[0].tool_call_id == "call-1"

    # 验证第二轮模型能看到工具结果。
    second_call_messages = provider.calls[1]
    assert any(message.tool_call_id == "call-1" for message in second_call_messages)

    # 验证工具事件顺序。
    assert EventType.TOOL_CALL in [event.type for event in events]
    assert EventType.TOOL_RESULT in [event.type for event in events]


def test_loop_sends_tool_error_back_to_model() -> None:
    """未知工具错误应回填给模型，而不是让程序崩溃。"""

    # 创建未知工具调用。
    tool_call = ToolCall(
        id="call-bad",
        function=ToolCallFunction(name="unknown_tool", arguments={}),
    )

    # 第一轮调用错误工具，第二轮返回解释。
    provider = FakeProvider(
        [
            Message.assistant(tool_calls=[tool_call]),
            Message.assistant("没有找到该工具。"),
        ]
    )

    # 创建 Agent Loop。
    loop = AgentLoop(provider, make_registry())

    # 执行任务。
    result = loop.run("调用一个不存在的工具")

    # 验证工具错误被记录。
    tool_message = next(message for message in result.messages if message.role.value == "tool")
    assert "工具执行失败" in tool_message.content
    assert result.final_content == "没有找到该工具。"


def test_loop_stops_at_max_steps() -> None:
    """模型持续调用工具时应被最大步数限制。"""

    # 创建只读取数学函数的工具调用。
    tool_call = ToolCall(
        id="call-1",
        function=ToolCallFunction(name="calculator", arguments={"expression": "1+1"}),
    )

    # 准备超过限制的相同响应。
    provider = FakeProvider([Message.assistant(tool_calls=[tool_call]) for _ in range(3)])

    # 设置最大两步。
    loop = AgentLoop(provider, make_registry(), max_steps=2)

    # 执行任务。
    result = loop.run("一直计算")

    # 验证达到限制。
    assert result.finished is False
    assert result.stop_reason == "max_steps"
    assert result.steps == 2
    assert "最大工具调用步数" in result.final_content
