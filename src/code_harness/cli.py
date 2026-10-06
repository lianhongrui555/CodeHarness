"""CodeHarness 命令行入口。"""

# 导入 argparse，用于解析命令参数。
import argparse

# 导入 sys，用于处理标准输入输出。
import sys

# 导入类型工具。
from pathlib import Path
from typing import Sequence

# 导入 Agent Loop。
from code_harness.agent.loop import AgentLoop, AgentLoopError, AgentRunResult
from code_harness.context.compressor import ContextCompressor

# 导入事件类型。
from code_harness.core.events import AgentEvent, EventType

# 导入消息类型。
from code_harness.core.messages import Message

# 导入 Ollama Provider。
from code_harness.providers.ollama import OllamaProvider
from code_harness.sessions.store import SessionStore

# 导入计算器工具和注册表。
from code_harness.tools.calculator import CalculatorTool
from code_harness.tools.filesystem import ListFilesTool, ReadFileTool
from code_harness.tools.registry import ToolRegistry
from code_harness.tools.search import SearchTextTool
from code_harness.tools.git_tools import GitDiffTool, GitLogTool, GitStatusTool
from code_harness.workspace import Workspace


def build_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器。"""

    # 创建解析器。
    parser = argparse.ArgumentParser(
        prog="code-harness",
        description="使用本地 Ollama 运行 CodeHarness 代码项目助手。",
    )

    # 添加一次性任务参数。
    parser.add_argument("task", nargs="?", help="要交给 Agent 的任务。")

    parser.add_argument("--workspace", help="允许 Agent 访问的项目目录，默认使用当前目录。")

    # 添加模型参数。
    parser.add_argument("--model", help="Ollama 模型名称，默认读取 OLLAMA_MODEL。")

    # 添加 Ollama 地址参数。
    parser.add_argument("--base-url", help="Ollama 服务地址。")

    # 添加最大循环步数。
    parser.add_argument("--max-steps", type=int, default=8, help="最大 Agent 循环步数。")

    # 添加温度参数。
    parser.add_argument("--temperature", type=float, default=0.1, help="模型温度。")

    # 添加会话编号参数。
    parser.add_argument("--session", help="保存或恢复指定的会话编号。")

    # 添加恢复会话参数。
    parser.add_argument("--resume", action="store_true", help="恢复 --session 指定的最新会话。")
    # 添加上下文 token 上限。
    parser.add_argument("--max-context-tokens", type=int, default=12000, help="触发上下文压缩的估算 token 上限。")

    # 添加最近消息保留数量。
    parser.add_argument("--keep-recent-messages", type=int, default=8, help="压缩时保留的最近消息数量。")
    # 添加强制交互模式。
    parser.add_argument("--interactive", action="store_true", help="进入连续对话模式。")

    # 返回解析器。
    return parser


def create_event_printer():
    """创建把事件打印到终端的函数。"""

    def print_event(event: AgentEvent) -> None:
        """根据事件类型输出易读信息。"""

        # 任务开始。
        if event.type is EventType.RUN_STARTED:
            print(f"[开始] 最大步数：{event.data.get('max_steps')}")

        # 助手决定调用工具。
        elif event.type is EventType.ASSISTANT_MESSAGE and event.data.get("tool_call_count"):
            print(f"[模型] 第 {event.data.get('step')} 轮决定调用工具")

        # 工具调用详情。
        elif event.type is EventType.TOOL_CALL:
            print(f"[工具] {event.data.get('name')} 参数={event.data.get('arguments')}")

        # 工具执行结果。
        elif event.type is EventType.TOOL_RESULT:
            prefix = "[工具错误]" if event.data.get("is_error") else "[工具结果]"
            print(f"{prefix} {event.data.get('result')}")

        # 上下文压缩完成。
        elif event.type is EventType.CONTEXT_COMPRESSED:
            print(
                f"[上下文] 已压缩 {event.data.get('before_count')} 条消息为 {event.data.get('after_count')} 条"
            )


        # 错误事件。
        elif event.type is EventType.ERROR:
            print(f"[错误] {event.data.get('message')}", file=sys.stderr)

    # 返回事件打印函数。
    return print_event


def create_runtime(args: argparse.Namespace) -> tuple[OllamaProvider, AgentLoop]:
    """根据命令行参数创建 Provider 和 Agent Loop。"""

    # 创建 Ollama Provider。
    provider = OllamaProvider(base_url=args.base_url, model=args.model)

    # 创建受限工作目录。
    workspace = Workspace(args.workspace or Path.cwd())

    # 创建工具注册表。
    registry = ToolRegistry()

    # 注册安全计算器。
    registry.register(CalculatorTool())

    # 注册只读文件工具。
    registry.register(ListFilesTool(workspace))
    registry.register(ReadFileTool(workspace))
    registry.register(SearchTextTool(workspace))
    registry.register(GitStatusTool(workspace))
    registry.register(GitDiffTool(workspace))
    registry.register(GitLogTool(workspace))

    # 创建上下文压缩器。
    context_compressor = ContextCompressor(
        provider=provider,
        max_tokens=args.max_context_tokens,
        keep_recent_messages=args.keep_recent_messages,
    )

    # 创建 Agent Loop。
    loop = AgentLoop(
        provider=provider,
        tools=registry,
        max_steps=args.max_steps,
        context_compressor=context_compressor,
        event_sink=create_event_printer(),
    )

    # 返回运行组件。
    return provider, loop


def run_task(loop: AgentLoop, task: str, history: list[Message] | None = None) -> AgentRunResult:
    """运行一次任务并打印最终回答。"""

    # 执行 Agent Loop。
    result = loop.run(task, history=history)

    # 打印空行，统一输出格式。
    print()

    # 打印最终回答。
    print(result.final_content)

    # 如果任务未正常完成，把状态写入标准错误。
    if not result.finished:
        print(f"[停止原因] {result.stop_reason}", file=sys.stderr)

    # 返回运行结果。
    return result


def run_interactive(loop: AgentLoop, session_store: SessionStore | None = None, session_id: str | None = None, history: list[Message] | None = None) -> int:
    """进入连续对话模式。"""

    # 显示操作提示。
    print("CodeHarness 已启动。")
    print("输入 /reset 清空会话，输入 /exit 退出。")

    # 保存会话消息历史。
    history: list[Message] = []

    # 持续等待用户输入。
    while True:
        # 使用 try 捕获 Ctrl+C 和 Ctrl+Z。
        try:
            # 等待用户输入。
            task = input("\n你：").strip()
        except (EOFError, KeyboardInterrupt):
            # 显示退出信息。
            print("\n已退出 CodeHarness。")
            # 返回成功退出码。
            return 0

        # 忽略空输入。
        if not task:
            continue

        # 退出命令。
        if task in {"/exit", "exit", "退出"}:
            print("已退出 CodeHarness。")
            return 0

        # 清空会话。
        if task in {"/reset", "reset", "新对话"}:
            history = []
            print("已清空会话历史。")
            continue

        # 执行任务。
        try:
            result = run_task(loop, task, history=history)
            history = result.messages
        except AgentLoopError as error:
            print(f"[失败] {error}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI 主入口。"""

    # 解析参数。
    parser = build_parser()
    args = parser.parse_args(argv)

    # 检查最大步数。
    if args.max_steps < 1:
        parser.error("--max-steps 必须大于等于 1")

    if args.max_context_tokens < 100:
        parser.error("--max-context-tokens 必须大于等于 100")

    if args.keep_recent_messages < 1:
        parser.error("--keep-recent-messages 必须大于等于 1")

    # --resume 必须同时指定 --session。
    if args.resume and not args.session:
        parser.error("--resume 必须和 --session 一起使用")

    # 创建会话存储。
    session_store = SessionStore(args.workspace or Path.cwd()) if args.session else None

    # 创建运行组件。
    provider, loop = create_runtime(args)

    # 使用 try/finally 确保 HTTP 连接关闭。
    try:
        # 按需恢复历史消息。
        history = session_store.load_latest(args.session) if args.resume and session_store and args.session else []

        # 没有任务或显式要求交互时进入连续对话。
        if args.interactive or not args.task:
            return run_interactive(
                loop,
                session_store=session_store,
                session_id=args.session,
                history=history,
            )

        # 运行一次性任务。
        result = run_task(loop, args.task, history=history)

        # 有会话编号时保存结果。
        if session_store is not None and args.session is not None:
            session_store.append_snapshot(args.session, result.messages)
            print(f"[会话] 已保存：{args.session}")

        return 0
    finally:
        # 关闭 Provider 连接。
        provider.close()


if __name__ == "__main__":
    # 把主函数返回值作为进程退出码。
    raise SystemExit(main())
