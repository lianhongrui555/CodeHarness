"""测试 Agent 消息和工具调用数据结构。"""

# 导入代理消息类型。
from code_harness.core.messages import Message, Role, ToolCall, ToolCallFunction


def test_user_message_serialization() -> None:
    """用户消息应能转换成接口字典。"""

    # 创建用户消息。
    message = Message.user("请解释这个项目")

    # 验证转换结果。
    assert message.to_api_dict() == {
        "role": "user",
        "content": "请解释这个项目",
    }


def test_assistant_tool_call_round_trip() -> None:
    """助手工具调用应能正确解析并再次序列化。"""

    # 模拟模型接口返回的助手消息。
    data = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call-1",
                "type": "function",
                "function": {
                    "name": "calculator",
                    "arguments": '{"expression": "1+1"}',
                },
            }
        ],
    }

    # 转换成内部消息对象。
    message = Message.from_api_dict(data)

    # 验证角色和工具调用。
    assert message.role is Role.ASSISTANT
    assert message.tool_calls[0].function.name == "calculator"
    assert message.tool_calls[0].function.arguments == {"expression": "1+1"}

    # 验证再次转换出去时仍使用 JSON 字符串参数。
    assert message.to_api_dict()["tool_calls"][0]["function"]["arguments"] == '{"expression": "1+1"}'


def test_tool_result_message() -> None:
    """工具结果消息必须保留对应调用编号。"""

    # 创建工具结果。
    message = Message.tool_result("call-1", "2", name="calculator")

    # 验证接口格式。
    assert message.to_api_dict() == {
        "role": "tool",
        "content": "2",
        "name": "calculator",
        "tool_call_id": "call-1",
    }


def test_invalid_tool_arguments_raise_error() -> None:
    """非法 JSON 参数应产生明确异常。"""

    # 使用 try/except 验证异常类型。
    try:
        ToolCall.from_api_dict(
            {
                "id": "call-bad",
                "function": {
                    "name": "calculator",
                    "arguments": "not-json",
                },
            }
        )
    except ValueError as error:
        # 验证错误提示可以帮助定位问题。
        assert "合法 JSON" in str(error)
    else:
        # 如果未抛出异常，则测试失败。
        raise AssertionError("非法工具参数没有被拦截")


def test_tool_call_function_requires_supported_arguments() -> None:
    """不支持的工具参数类型必须报错。"""

    # 使用 try/except 验证异常类型。
    try:
        ToolCallFunction.from_api_dict({"name": "calculator", "arguments": 123})
    except TypeError as error:
        # 验证错误提示包含参数类型。
        assert "int" in str(error)
    else:
        # 如果未抛出异常，则测试失败。
        raise AssertionError("不支持的参数类型没有被拦截")
