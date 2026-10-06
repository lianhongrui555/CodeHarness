"""测试工具系统。"""

# 导入 pytest。
import pytest

# 导入工具类和异常。
from code_harness.tools.base import ToolError, ToolValidationError
from code_harness.tools.calculator import CalculatorTool
from code_harness.tools.registry import ToolRegistry


def test_calculator_common_expressions() -> None:
    """计算器应支持常见运算。"""

    # 创建计算器。
    calculator = CalculatorTool()

    # 验证乘法。
    assert calculator.execute(expression="12345*6789") == "83810205"

    # 验证括号和优先级。
    assert calculator.execute(expression="(12+3)*4") == "60"

    # 验证幂运算。
    assert calculator.execute(expression="2**10") == "1024"

    # 验证除法结果会去掉多余的小数零。
    assert calculator.execute(expression="8/2") == "4"


def test_calculator_rejects_unsafe_expressions() -> None:
    """计算器不得执行函数、名称或导入。"""

    # 创建计算器。
    calculator = CalculatorTool()

    # 拒绝函数调用。
    with pytest.raises(ToolError):
        calculator.execute(expression="__import__('os').system('dir')")

    # 拒绝普通名称。
    with pytest.raises(ToolError):
        calculator.execute(expression="x + 1")


def test_calculator_rejects_invalid_or_dangerous_values() -> None:
    """计算器应拦截除零、超大幂和非法语法。"""

    # 创建计算器。
    calculator = CalculatorTool()

    # 除零应失败。
    with pytest.raises(ToolError, match="除数不能为零"):
        calculator.execute(expression="1/0")

    # 超大指数应失败。
    with pytest.raises(ToolError, match="指数不能超过"):
        calculator.execute(expression="2**101")

    # 非法语法应失败。
    with pytest.raises(ToolError, match="格式错误"):
        calculator.execute(expression="1+")


def test_registry_register_and_execute() -> None:
    """工具注册表应能查找并执行工具。"""

    # 创建注册表并注册计算器。
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    # 验证工具列表和模型定义。
    assert [tool.name for tool in registry.list_tools()] == ["calculator"]
    assert registry.to_api_schemas()[0]["function"]["name"] == "calculator"

    # 执行工具。
    assert registry.execute("calculator", {"expression": "6*7"}) == "42"


def test_registry_rejects_duplicate_unknown_and_invalid_arguments() -> None:
    """注册表应拒绝重复工具、未知工具和错误参数。"""

    # 创建注册表。
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    # 拒绝重复注册。
    with pytest.raises(ToolError, match="名称重复"):
        registry.register(CalculatorTool())

    # 拒绝未知工具。
    with pytest.raises(ToolError, match="工具不存在"):
        registry.execute("unknown", {})

    # 拒绝缺失参数。
    with pytest.raises(ToolValidationError, match="缺少参数"):
        registry.execute("calculator", {})

    # 拒绝未知参数。
    with pytest.raises(ToolValidationError, match="未知参数"):
        registry.execute("calculator", {"expression": "1+1", "extra": "bad"})
