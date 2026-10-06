"""测试 CodeHarness 命令行入口。"""

# 导入 argparse 类型。
import argparse

# 导入 CLI 函数。
from code_harness.cli import build_parser, create_event_printer

# 导入事件类型。
from code_harness.core.events import AgentEvent, EventType


def test_cli_defaults() -> None:
    """命令行应提供默认模型循环参数。"""

    # 解析空参数。
    args = build_parser().parse_args(["请计算 1+1"])

    # 验证任务和默认值。
    assert args.task == "请计算 1+1"
    assert args.max_steps == 8
    assert args.temperature == 0.1
    assert args.interactive is False
    assert args.workspace is None
    assert args.session is None
    assert args.resume is False


def test_event_printer_outputs_tool_result(capsys) -> None:
    """事件打印函数应输出工具结果。"""

    # 创建打印函数。
    printer = create_event_printer()

    # 发送工具结果事件。
    printer(
        AgentEvent(
            type=EventType.TOOL_RESULT,
            data={"result": "2", "is_error": False},
        )
    )

    # 读取标准输出。
    captured = capsys.readouterr()

    # 验证输出内容。
    assert "[工具结果] 2" in captured.out
