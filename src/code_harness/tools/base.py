"""工具系统的统一接口。"""

# 导入抽象基类工具。
from abc import ABC, abstractmethod

# 导入类型工具。
from typing import Any


class ToolError(RuntimeError):
    """表示工具执行失败。"""


class ToolValidationError(ToolError):
    """表示工具参数不符合要求。"""


class BaseTool(ABC):
    """所有工具都必须遵守的接口。"""

    # 工具的唯一名称。
    name: str

    # 工具用途说明，模型会根据它决定何时调用。
    description: str

    # 参数 JSON Schema。
    parameters_schema: dict[str, Any]

    def to_api_schema(self) -> dict[str, Any]:
        """转换成 Ollama/OpenAI Function Calling 结构。"""

        # 返回标准工具定义。
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }

    def validate_arguments(self, arguments: dict[str, Any]) -> None:
        """执行基础参数校验。"""

        # 读取必填参数列表。
        required = self.parameters_schema.get("required", [])

        # 检查是否缺少必填参数。
        missing = [name for name in required if name not in arguments]

        # 缺少参数时给出明确错误。
        if missing:
            raise ToolValidationError(f"工具 {self.name} 缺少参数：{', '.join(missing)}")

        # 读取允许的参数定义。
        properties = self.parameters_schema.get("properties", {})

        # 检查是否传入未定义参数。
        extra = [name for name in arguments if name not in properties]

        # 多余参数直接拒绝，避免模型误传。
        if extra:
            raise ToolValidationError(f"工具 {self.name} 收到未知参数：{', '.join(extra)}")

        # 逐个检查参数类型。
        for name, value in arguments.items():
            # 读取该参数声明的 JSON Schema 类型。
            expected_type = properties[name].get("type")

            # 检查字符串类型。
            if expected_type == "string" and not isinstance(value, str):
                raise ToolValidationError(f"工具 {self.name} 的参数 {name} 必须是字符串")

            # 检查数字类型，并排除布尔值。
            if expected_type in {"number", "integer"} and (
                isinstance(value, bool) or not isinstance(value, (int, float))
            ):
                raise ToolValidationError(f"工具 {self.name} 的参数 {name} 必须是数字")

            # 检查布尔类型。
            if expected_type == "boolean" and not isinstance(value, bool):
                raise ToolValidationError(f"工具 {self.name} 的参数 {name} 必须是布尔值")

    @abstractmethod
    def execute(self, **arguments: Any) -> str:
        """执行工具并返回文本结果。"""

        # 抽象方法由具体工具实现。
        raise NotImplementedError
