"""安全的数学计算工具。"""

# 导入 AST 工具，用于解析而不是直接执行表达式。
import ast

# 导入数学常量。
import math

# 导入类型工具。
from typing import Any

# 导入工具基类和异常。
from code_harness.tools.base import BaseTool, ToolError


class CalculatorTool(BaseTool):
    """计算基础数学表达式。"""

    # 定义工具名称。
    name = "calculator"

    # 定义工具说明。
    description = "计算包含加减乘除、括号、取余和幂运算的数学表达式。"

    # 定义参数结构。
    parameters_schema = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "需要计算的数学表达式，例如 (12+3)*4。",
            }
        },
        "required": ["expression"],
        "additionalProperties": False,
    }

    # 定义表达式最大长度。
    MAX_EXPRESSION_LENGTH = 200

    # 定义幂运算指数上限，防止构造超大数据。
    MAX_POWER = 100

    # 定义结果绝对值上限。
    MAX_RESULT = 1e100

    def _evaluate_node(self, node: ast.AST) -> int | float:
        """递归计算 AST 节点。"""

        # 处理普通数字。
        if isinstance(node, ast.Constant):
            # 拒绝布尔值，因为 bool 是 int 的子类。
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise ToolError("表达式中只能包含数字")
            # 返回数字。
            return node.value

        # 处理加减乘除等二元表达式。
        if isinstance(node, ast.BinOp):
            # 先计算左侧。
            left = self._evaluate_node(node.left)
            # 再计算右侧。
            right = self._evaluate_node(node.right)

            # 加法。
            if isinstance(node.op, ast.Add):
                result = left + right
            # 减法。
            elif isinstance(node.op, ast.Sub):
                result = left - right
            # 乘法。
            elif isinstance(node.op, ast.Mult):
                result = left * right
            # 除法。
            elif isinstance(node.op, ast.Div):
                if right == 0:
                    raise ToolError("除数不能为零")
                result = left / right
            # 整除。
            elif isinstance(node.op, ast.FloorDiv):
                if right == 0:
                    raise ToolError("除数不能为零")
                result = left // right
            # 取余。
            elif isinstance(node.op, ast.Mod):
                if right == 0:
                    raise ToolError("除数不能为零")
                result = left % right
            # 幂运算。
            elif isinstance(node.op, ast.Pow):
                if abs(right) > self.MAX_POWER:
                    raise ToolError(f"幂运算指数不能超过 {self.MAX_POWER}")
                result = left**right
            # 其他运算符全部拒绝。
            else:
                raise ToolError(f"不支持的运算符：{type(node.op).__name__}")

            # 检查数值范围。
            if isinstance(result, complex) or abs(result) > self.MAX_RESULT:
                raise ToolError("计算结果超出安全范围")
            # 返回结果。
            return result

        # 处理正号和负号。
        if isinstance(node, ast.UnaryOp):
            # 计算操作数。
            operand = self._evaluate_node(node.operand)
            # 正号。
            if isinstance(node.op, ast.UAdd):
                return operand
            # 负号。
            if isinstance(node.op, ast.USub):
                return -operand
            # 其他一元运算拒绝。
            raise ToolError(f"不支持的一元运算符：{type(node.op).__name__}")

        # 其他 AST 节点全部拒绝。
        raise ToolError(f"不支持的表达式结构：{type(node).__name__}")

    def execute(self, **arguments: Any) -> str:
        """执行数学计算。"""

        # 校验参数。
        self.validate_arguments(arguments)

        # 读取表达式并去掉首尾空格。
        expression = arguments["expression"].strip()

        # 空表达式直接拒绝。
        if not expression:
            raise ToolError("数学表达式不能为空")

        # 限制表达式长度。
        if len(expression) > self.MAX_EXPRESSION_LENGTH:
            raise ToolError(f"数学表达式不能超过 {self.MAX_EXPRESSION_LENGTH} 个字符")

        # 使用 try 把语法错误转换成工具错误。
        try:
            # 解析表达式，但绝不直接执行 eval。
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as error:
            raise ToolError(f"数学表达式格式错误：{error.msg}") from error

        # 递归计算表达式。
        result = self._evaluate_node(tree.body)

        # 浮点数接近整数时转换成整数，避免显示 3.0。
        if isinstance(result, float) and result.is_integer():
            return str(int(result))

        # 返回普通结果字符串。
        return str(result)
