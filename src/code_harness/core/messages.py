"""Agent 消息和工具调用的数据结构。"""

# 导入 dataclass，用于创建结构清晰且不易写错的数据对象。
from dataclasses import dataclass, field

# 导入枚举类型，用于限制消息角色。
from enum import StrEnum

# 导入 JSON 工具，用于处理模型返回的工具参数。
import json

# 导入类型工具，用于标注复杂数据结构。
from typing import Any


class Role(StrEnum):
    """表示一条消息由谁产生。"""

    # 系统消息用于给模型设定行为规则。
    SYSTEM = "system"

    # 用户消息表示人类提出的问题或任务。
    USER = "user"

    # 助手消息表示模型生成的回答或工具调用。
    ASSISTANT = "assistant"

    # 工具消息表示某个工具执行后的结果。
    TOOL = "tool"


@dataclass(slots=True)
class ToolCallFunction:
    """表示模型要求调用的工具函数。"""

    # name 是工具名称，例如 calculator。
    name: str

    # arguments 是工具参数，统一保存为 Python 字典。
    arguments: dict[str, Any] = field(default_factory=dict)

    def to_api_dict(self) -> dict[str, Any]:
        """转换成 Ollama/OpenAI 兼容接口需要的格式。"""

        # arguments 必须序列化成 JSON 字符串。
        return {
            "name": self.name,
            "arguments": json.dumps(self.arguments, ensure_ascii=False),
        }

    @classmethod
    def from_api_dict(cls, data: dict[str, Any]) -> "ToolCallFunction":
        """从模型接口返回的数据创建工具函数对象。"""

        # 读取工具名称，不存在时使用空字符串。
        name = str(data.get("name", ""))

        # 读取参数，接口可能返回字典或 JSON 字符串。
        raw_arguments = data.get("arguments", {})

        # 如果参数是字符串，就尝试解析成字典。
        if isinstance(raw_arguments, str):
            try:
                # 解析 JSON 字符串；空字符串按空字典处理。
                arguments = json.loads(raw_arguments) if raw_arguments else {}
            except json.JSONDecodeError as error:
                # 参数格式错误时给出明确异常，方便定位模型输出问题。
                raise ValueError(f"工具参数不是合法 JSON：{raw_arguments}") from error
        # 如果参数已经是字典，就直接使用。
        elif isinstance(raw_arguments, dict):
            arguments = raw_arguments
        # 其他格式统一视为错误。
        else:
            raise TypeError(f"不支持的工具参数类型：{type(raw_arguments).__name__}")

        # 返回结构化对象。
        return cls(name=name, arguments=arguments)


@dataclass(slots=True)
class ToolCall:
    """表示模型发起的一次完整工具调用。"""

    # id 用于把工具结果和原始调用对应起来。
    id: str

    # function 保存工具名称和参数。
    function: ToolCallFunction

    # type 当前固定为 function。
    type: str = "function"

    def to_api_dict(self) -> dict[str, Any]:
        """转换成接口需要的工具调用格式。"""

        # 返回统一格式。
        return {
            "id": self.id,
            "type": self.type,
            "function": self.function.to_api_dict(),
        }

    @classmethod
    def from_api_dict(cls, data: dict[str, Any]) -> "ToolCall":
        """从模型接口返回的数据创建工具调用对象。"""

        # 读取函数数据；缺失时使用空字典。
        function_data = data.get("function") or {}

        # 返回结构化工具调用。
        return cls(
            id=str(data.get("id", "")),
            type=str(data.get("type", "function")),
            function=ToolCallFunction.from_api_dict(function_data),
        )


@dataclass(slots=True)
class Message:
    """表示 Agent 对话中的一条消息。"""

    # role 表示消息来源。
    role: Role

    # content 保存文本内容。
    content: str = ""

    # name 可用于标记工具名称。
    name: str | None = None

    # tool_calls 仅由助手消息使用。
    tool_calls: list[ToolCall] = field(default_factory=list)

    # tool_call_id 仅由工具结果消息使用。
    tool_call_id: str | None = None

    def to_api_dict(self) -> dict[str, Any]:
        """转换成 Ollama/OpenAI 兼容接口需要的消息格式。"""

        # 创建基础消息。
        result: dict[str, Any] = {
            "role": self.role.value,
            "content": self.content,
        }

        # 有工具名称时加入 name。
        if self.name is not None:
            result["name"] = self.name

        # 助手存在工具调用时加入 tool_calls。
        if self.tool_calls:
            result["tool_calls"] = [tool_call.to_api_dict() for tool_call in self.tool_calls]

        # 工具结果消息必须携带 tool_call_id。
        if self.tool_call_id is not None:
            result["tool_call_id"] = self.tool_call_id

        # 返回接口格式。
        return result

    @classmethod
    def from_api_dict(cls, data: dict[str, Any]) -> "Message":
        """从模型接口返回的数据创建消息对象。"""

        # 解析角色字符串。
        role = Role(str(data.get("role", Role.ASSISTANT.value)))

        # 读取文本内容；接口有时返回 null，因此统一转换成空字符串。
        content = data.get("content") or ""

        # 读取工具调用列表。
        raw_tool_calls = data.get("tool_calls") or []

        # 把每条工具调用转换成内部对象。
        tool_calls = [ToolCall.from_api_dict(item) for item in raw_tool_calls]

        # 返回结构化消息。
        return cls(
            role=role,
            content=str(content),
            name=data.get("name"),
            tool_calls=tool_calls,
            tool_call_id=data.get("tool_call_id"),
        )

    @classmethod
    def system(cls, content: str) -> "Message":
        """创建系统消息。"""

        # 返回系统角色消息。
        return cls(role=Role.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> "Message":
        """创建用户消息。"""

        # 返回用户角色消息。
        return cls(role=Role.USER, content=content)

    @classmethod
    def assistant(cls, content: str = "", tool_calls: list[ToolCall] | None = None) -> "Message":
        """创建助手消息。"""

        # 返回助手角色消息，并安全复制工具调用列表。
        return cls(role=Role.ASSISTANT, content=content, tool_calls=list(tool_calls or []))

    @classmethod
    def tool_result(cls, tool_call_id: str, content: str, name: str | None = None) -> "Message":
        """创建工具结果消息。"""

        # 返回工具角色消息，并保存对应的调用编号。
        return cls(role=Role.TOOL, content=content, name=name, tool_call_id=tool_call_id)
