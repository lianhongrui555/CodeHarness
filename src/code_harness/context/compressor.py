"""Agent 上下文压缩。"""

# 导入数学工具，用于向上取整。
import math

# 导入类型工具。
from typing import Any

# 导入消息类型。
from code_harness.core.messages import Message, Role

# 导入模型供应商接口。
from code_harness.providers.base import BaseProvider, ProviderError


class ContextCompressionError(RuntimeError):
    """表示上下文压缩失败。"""


class ContextCompressor:
    """在上下文过长时总结较早的历史消息。"""

    def __init__(
        self,
        provider: BaseProvider,
        max_tokens: int = 12000,
        keep_recent_messages: int = 8,
        max_transcript_chars: int = 12000,
    ) -> None:
        """初始化压缩器。"""

        # 保存模型供应商，用于生成摘要。
        self.provider = provider

        # 超过该估算值后触发压缩。
        self.max_tokens = max_tokens

        # 最近消息始终保留。
        self.keep_recent_messages = keep_recent_messages

        # 摘要输入的最大字符数，避免摘要请求本身过长。
        self.max_transcript_chars = max_transcript_chars

    def estimate_tokens(self, messages: list[Message]) -> int:
        """粗略估算消息 token 数量。"""

        # 累计所有消息文本。
        text_parts: list[str] = []

        # 逐个转换消息。
        for message in messages:
            # 加入角色和正文。
            text_parts.append(f"{message.role.value}:{message.content}")

            # 加入工具调用信息。
            for tool_call in message.tool_calls:
                text_parts.append(
                    f"tool_call:{tool_call.function.name}:{tool_call.function.arguments}"
                )

        # 合并文本。
        text = "\n".join(text_parts)

        # 混合中英文按约 3 个字符一个 token 估算。
        return max(1, math.ceil(len(text) / 3))

    def _message_to_text(self, message: Message) -> str:
        """把一条消息转换成摘要输入。"""

        # 工具调用额外展示名称和参数。
        tool_call_text = ""
        if message.tool_calls:
            tool_call_text = " 工具调用=" + "; ".join(
                f"{call.function.name}({call.function.arguments})" for call in message.tool_calls
            )

        # 工具结果展示工具名称。
        tool_name = f" 工具={message.name}" if message.name else ""

        # 返回摘要文本。
        return f"{message.role.value}{tool_name}: {message.content}{tool_call_text}"

    def _recent_start(self, messages: list[Message]) -> int:
        """计算最近消息的起点，并保证工具结果不脱离调用。"""

        # 至少保留最近 N 条。
        start = max(0, len(messages) - self.keep_recent_messages)

        # 如果起点是工具结果，就向前找到包含对应调用编号的助手消息。
        while start > 0 and messages[start].role is Role.TOOL:
            # 读取当前工具结果对应的调用编号。
            tool_call_id = messages[start].tool_call_id

            # 向前移动至少一条。
            start -= 1

            # 继续向前查找匹配的助手工具调用。
            while start > 0:
                candidate = messages[start]
                has_matching_call = (
                    candidate.role is Role.ASSISTANT
                    and any(call.id == tool_call_id for call in candidate.tool_calls)
                )
                if has_matching_call:
                    break
                start -= 1

        # 返回安全起点。
        return start

    def compress(self, messages: list[Message]) -> list[Message]:
        """按需压缩消息，不需要压缩时返回原列表。"""

        # 计算压缩前的 token 估算。
        before_tokens = self.estimate_tokens(messages)

        # 没有超过阈值就不处理。
        if before_tokens <= self.max_tokens:
            return messages

        # 计算最近消息起点。
        recent_start = self._recent_start(messages)

        # 提取系统消息。
        system_messages = [message for message in messages if message.role is Role.SYSTEM]

        # 提取需要总结的旧消息。
        older_messages = [
            message
            for message in messages[:recent_start]
            if message.role is not Role.SYSTEM
        ]

        # 没有可压缩内容时保留原列表。
        if not older_messages:
            return messages

        # 把旧消息转换成纯文本。
        transcript = "\n".join(self._message_to_text(message) for message in older_messages)

        # 控制摘要输入长度。
        if len(transcript) > self.max_transcript_chars:
            transcript = transcript[: self.max_transcript_chars] + "\n...（历史内容已截断）"

        # 构造摘要提示。
        summary_messages = [
            Message.system(
                "你是上下文压缩器。请把历史会话压缩成事实准确、结构清晰的中文摘要。"
                "保留用户目标、关键决定、工具结果、未解决问题和下一步。不要编造信息。"
            ),
            Message.user(f"请总结以下历史会话：\n\n{transcript}"),
        ]

        # 使用 try 调用模型生成摘要。
        try:
            summary_message = self.provider.chat(summary_messages, temperature=0)
        except ProviderError as error:
            raise ContextCompressionError(f"生成上下文摘要失败：{error}") from error

        # 摘要不能为空。
        summary = summary_message.content.strip()
        if not summary:
            raise ContextCompressionError("模型返回了空摘要")

        # 创建摘要系统消息。
        summary_context = Message.system(f"以下是之前会话的压缩摘要：\n{summary}")

        # 保留最近消息。
        recent_messages = messages[recent_start:]

        # 组装压缩后的上下文。
        compressed = [*system_messages, summary_context, *recent_messages]

        # 只有压缩后确实变短时才使用摘要，避免短会话反而膨胀。
        if self.estimate_tokens(compressed) >= before_tokens:
            return messages

        # 返回压缩后的上下文。
        return compressed
        return [*system_messages, summary_context, *recent_messages]
