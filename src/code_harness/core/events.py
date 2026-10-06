"""Agent 运行过程中的可观察事件。"""

# 导入 dataclass 工具。
from dataclasses import dataclass, field

# 导入枚举类型。
from enum import StrEnum

# 导入类型工具。
from typing import Any


class EventType(StrEnum):
    """表示 Agent 运行事件的类型。"""

    # 一次 Agent 运行开始。
    RUN_STARTED = "run_started"

    # 模型生成了一条助手消息。
    ASSISTANT_MESSAGE = "assistant_message"

    # 模型请求调用工具。
    TOOL_CALL = "tool_call"

    # 工具执行完成。
    TOOL_RESULT = "tool_result"

    # 上下文完成压缩。
    CONTEXT_COMPRESSED = "context_compressed"

    # 一次 Agent 运行结束。
    RUN_FINISHED = "run_finished"

    # 运行过程中发生错误。
    ERROR = "error"


@dataclass(slots=True)
class AgentEvent:
    """保存一个可观察事件。"""

    # type 表示事件类型。
    type: EventType

    # data 保存事件详情。
    data: dict[str, Any] = field(default_factory=dict)
