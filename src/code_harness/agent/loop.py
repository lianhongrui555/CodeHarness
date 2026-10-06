"""CodeHarness 的最小 Agent Loop。"""

# 导入 dataclass 工具。
from dataclasses import dataclass, field

# 导入类型工具。
from typing import Callable

# 导入事件类型。
from code_harness.context.compressor import ContextCompressionError, ContextCompressor
from code_harness.core.events import AgentEvent, EventType

# 导入消息类型。
from code_harness.core.messages import Message

# 导入模型接口。
from code_harness.providers.base import BaseProvider, ProviderError

# 导入工具异常和注册表。
from code_harness.tools.base import ToolError
from code_harness.tools.registry import ToolRegistry

# 定义事件处理函数类型。
EventSink = Callable[[AgentEvent], None]

# 定义默认系统提示词。
DEFAULT_SYSTEM_PROMPT = (
    "你是 CodeHarness，一个运行在本地的代码项目助手。"
    "需要事实时必须使用工具，不能编造工具结果。"
    "任务完成后，用简洁清楚的中文总结结果。"
)


class AgentLoopError(RuntimeError):
    """表示 Agent Loop 无法继续运行。"""


@dataclass(slots=True)
class AgentRunResult:
    """保存一次 Agent 运行的完整结果。"""

    # final_content 是最终给用户的回答。
    final_content: str

    # messages 是完整消息历史。
    messages: list[Message] = field(default_factory=list)

    # steps 表示调用模型的轮数。
    steps: int = 0

    # stop_reason 表示停止原因。
    stop_reason: str = "completed"

    # finished 表示任务是否正常完成。
    finished: bool = True


class AgentLoop:
    """执行“模型思考 → 工具调用 → 继续思考”的循环。"""

    def __init__(
        self,
        provider: BaseProvider,
        tools: ToolRegistry,
        max_steps: int = 8,
        context_compressor: ContextCompressor | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        event_sink: EventSink | None = None,
    ) -> None:
        """初始化 Agent Loop。"""

        # 保存模型供应商。
        self.provider = provider

        # 保存工具注册表。
        self.tools = tools

        # 限制最大模型调用轮数。
        self.max_steps = max_steps

        # 保存可选的上下文压缩器。
        self.context_compressor = context_compressor

        # 保存系统提示词。
        self.system_prompt = system_prompt

        # 保存事件接收函数。
        self.event_sink = event_sink

    def _emit(self, event_type: EventType, **data: object) -> None:
        """发送事件。"""

        # 没有事件接收函数时直接返回。
        if self.event_sink is None:
            return

        # 构造并发送事件。
        self.event_sink(AgentEvent(type=event_type, data=dict(data)))

    def run(self, task: str, history: list[Message] | None = None) -> AgentRunResult:
        """执行一个用户任务。"""

        # 清理任务文本。
        task = task.strip()

        # 空任务拒绝执行。
        if not task:
            raise AgentLoopError("任务内容不能为空")

        # 复制历史消息，避免修改调用者传入的列表。
        messages = list(history or [])

        # 如果没有历史消息，就加入系统提示和用户任务。
        if not messages:
            messages.extend([Message.system(self.system_prompt), Message.user(task)])
        # 如果存在历史消息，就只追加本次用户任务。
        else:
            messages.append(Message.user(task))

        # 发送运行开始事件。
        self._emit(EventType.RUN_STARTED, task=task, max_steps=self.max_steps)

        # 读取工具定义。
        tool_schemas = self.tools.to_api_schemas()

        # 标记当前是否存在未解决的工具错误。
        error_recovery_pending = False

        # 限制模型在工具失败后忽略错误直接作答的次数。
        error_recovery_attempts = 0

        # 保存最后一次工具错误。
        last_tool_error = ""
        # 逐轮执行 Agent Loop。
        for step in range(1, self.max_steps + 1):
            # 在调用模型前按需压缩上下文。
            if self.context_compressor is not None:
                # 记录压缩前的消息数量。
                before_count = len(messages)

                # 记录压缩前的估算 token 数。
                before_tokens = self.context_compressor.estimate_tokens(messages)

                # 使用 try 捕获摘要错误。
                try:
                    # 执行压缩。
                    compressed_messages = self.context_compressor.compress(messages)
                except ContextCompressionError as error:
                    # 发送错误事件。
                    self._emit(EventType.ERROR, stage="compression", message=str(error))
                    # 终止本次运行。
                    raise AgentLoopError(f"上下文压缩失败：{error}") from error

                # 只有确实发生变化时才替换消息列表。
                if compressed_messages is not messages:
                    messages = compressed_messages

                    # 发送压缩完成事件。
                    self._emit(
                        EventType.CONTEXT_COMPRESSED,
                        before_count=before_count,
                        after_count=len(messages),
                        before_tokens=before_tokens,
                        after_tokens=self.context_compressor.estimate_tokens(messages),
                    )
            # 使用 try 捕获模型错误。
            try:
                # 调用模型，并把完整消息历史发过去。
                assistant_message = self.provider.chat(messages, tools=tool_schemas or None)
            except ProviderError as error:
                # 发送错误事件。
                self._emit(EventType.ERROR, stage="provider", message=str(error))
                # 转换成 Agent Loop 异常。
                raise AgentLoopError(f"模型调用失败：{error}") from error

            # 把助手消息加入历史。
            messages.append(assistant_message)

            # 发送助手消息事件。
            self._emit(
                EventType.ASSISTANT_MESSAGE,
                step=step,
                content=assistant_message.content,
                tool_call_count=len(assistant_message.tool_calls),
            )

            # 如果没有工具调用，说明模型准备给出最终回答。
            if not assistant_message.tool_calls:
                # 如果上一次工具失败，不能直接接受模型回答。
                if error_recovery_pending:
                    # 记录模型再次忽略工具错误的次数。
                    error_recovery_attempts += 1

                    # 超过一次修正机会后，拒绝模型编造结果。
                    if error_recovery_attempts > 1:
                        # 生成明确、不可验证的失败回答。
                        final_content = "工具执行失败，未获得可验证结果。"

                        # 发出错误事件。
                        self._emit(
                            EventType.ERROR,
                            stage="tool_recovery",
                            message=f"模型未重新调用工具，最后错误：{last_tool_error}",
                        )

                        # 发出运行结束事件。
                        self._emit(EventType.RUN_FINISHED, steps=step, stop_reason="tool_error")

                        # 返回失败结果，而不是接受编造内容。
                        return AgentRunResult(
                            final_content=final_content,
                            messages=messages,
                            steps=step,
                            stop_reason="tool_error",
                            finished=False,
                        )

                    # 提醒模型必须修正参数并重新调用工具。
                    messages.append(
                        Message.system(
                            "上一次工具调用失败。不得根据记忆或猜测编造工具结果。"
                            "你必须使用真实参数重新调用工具；如果无法完成，请明确说明工具执行失败。"
                        )
                    )

                    # 进入下一轮，让模型有机会修正。
                    continue

                # 没有工具错误时正常返回最终回答。
                self._emit(EventType.RUN_FINISHED, steps=step, stop_reason="completed")
                return AgentRunResult(
                    final_content=assistant_message.content,
                    messages=messages,
                    steps=step,
                    stop_reason="completed",
                    finished=True,
                )

            # 逐个执行模型请求的工具。
            # 记录本轮工具调用是否发生错误。
            cycle_had_error = False
            for tool_call in assistant_message.tool_calls:
                # 读取工具名称和参数。
                tool_name = tool_call.function.name
                arguments = tool_call.function.arguments

                # 发送工具调用事件。
                self._emit(
                    EventType.TOOL_CALL,
                    step=step,
                    tool_call_id=tool_call.id,
                    name=tool_name,
                    arguments=arguments,
                )

                # 默认认为工具没有错误。
                is_error = False

                # 使用 try 捕获工具错误。
                try:
                    # 执行工具。
                    tool_result = self.tools.execute(tool_name, arguments)
                except ToolError as error:
                    # 将工具错误转成可回填给模型的文本。
                    tool_result = f"工具执行失败：{error}"
                    is_error = True
                    cycle_had_error = True
                    last_tool_error = str(error)

                # 把工具结果加入消息历史。
                messages.append(Message.tool_result(tool_call.id, tool_result, name=tool_name))

                # 发送工具结果事件。
                self._emit(
                    EventType.TOOL_RESULT,
                    step=step,
                    tool_call_id=tool_call.id,
                    name=tool_name,
                    result=tool_result,
                    is_error=is_error,
                )

            # 根据本轮结果更新错误恢复状态。
            if cycle_had_error:
                error_recovery_pending = True
            else:
                error_recovery_pending = False
                error_recovery_attempts = 0

        # 达到最大步数后停止，避免无限循环。
        self._emit(EventType.RUN_FINISHED, steps=self.max_steps, stop_reason="max_steps")

        # 返回未正常完成的结果。
        return AgentRunResult(
            final_content="达到最大工具调用步数，任务已停止。",
            messages=messages,
            steps=self.max_steps,
            stop_reason="max_steps",
            finished=False,
        )
