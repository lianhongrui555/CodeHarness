"""工具注册表。"""

# 导入类型工具。
from typing import Any

# 导入工具接口和异常。
from code_harness.tools.base import BaseTool, ToolError


class ToolRegistry:
    """管理所有可供 Agent 调用的工具。"""

    def __init__(self) -> None:
        """初始化空工具表。"""

        # 使用字典保存工具名称与工具对象。
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册一个工具。"""

        # 拒绝重复名称，防止模型调用到错误工具。
        if tool.name in self._tools:
            raise ToolError(f"工具名称重复：{tool.name}")

        # 保存工具。
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        """按名称获取工具。"""

        # 查询工具。
        tool = self._tools.get(name)

        # 工具不存在时给出明确错误。
        if tool is None:
            raise ToolError(f"工具不存在：{name}")

        # 返回工具。
        return tool

    def list_tools(self) -> list[BaseTool]:
        """返回全部工具。"""

        # 按名称排序，保证输出稳定。
        return [self._tools[name] for name in sorted(self._tools)]

    def to_api_schemas(self) -> list[dict[str, Any]]:
        """返回模型需要的工具定义列表。"""

        # 逐个转换工具结构。
        return [tool.to_api_schema() for tool in self.list_tools()]

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """执行指定工具。"""

        # 获取工具。
        tool = self.get(name)

        # 校验并执行工具。
        return tool.execute(**arguments)
