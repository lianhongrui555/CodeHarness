"""代码文本搜索工具。"""

# 导入文件名匹配工具。
from fnmatch import fnmatch

# 导入操作系统遍历接口。
import os

# 导入路径类型。
from pathlib import Path

# 导入类型工具。
from typing import Any, Iterator

# 导入工作目录和异常。
from code_harness.workspace import Workspace, WorkspaceError

# 导入工具基类。
from code_harness.tools.base import BaseTool, ToolError


class SearchTextTool(BaseTool):
    """在项目文本文件中搜索指定字符串。"""

    # 工具名称。
    name = "search_text"

    # 工具说明。
    description = "在代码项目中搜索函数、类、变量、配置或错误关键字，返回文件路径和行号。"

    # 参数定义。
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "要搜索的普通文本，不是正则表达式。",
            },
            "path": {
                "type": "string",
                "description": "相对工作目录的搜索路径，默认 .。",
            },
            "file_pattern": {
                "type": "string",
                "description": "文件名匹配模式，例如 *.py 或 *.md，默认 *。",
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "是否区分大小写，默认 false。",
            },
            "max_results": {
                "type": "integer",
                "description": "最多返回的匹配行数，默认 100，最大 500。",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    # 单个文件最大读取体积。
    MAX_FILE_SIZE = 512 * 1024

    # 默认最大结果数。
    DEFAULT_RESULTS = 100

    # 最大结果数上限。
    MAX_RESULTS = 500

    def __init__(self, workspace: Workspace) -> None:
        """保存工作目录。"""

        # 保存安全边界。
        self.workspace = workspace

    def _iter_files(self, target: Path) -> Iterator[Path]:
        """遍历目标路径内的安全文本文件。"""

        # 如果目标是单个文件，直接返回。
        if target.is_file():
            yield target
            return

        # 递归遍历目录。
        for current_root, directory_names, file_names in os.walk(target):
            # 过滤隐藏、缓存、依赖和敏感目录。
            directory_names[:] = sorted(
                name
                for name in directory_names
                if not self.workspace.is_sensitive(Path(current_root) / name)
                and not self.workspace.is_ignored(Path(current_root) / name)
            )

            # 逐个返回安全文件。
            for file_name in sorted(file_names):
                file_path = Path(current_root) / file_name

                # 跳过敏感文件。
                if self.workspace.is_sensitive(file_path):
                    continue

                # 跳过被忽略的缓存或构建文件。
                if self.workspace.is_ignored(file_path):
                    continue

                # 返回文件。
                yield file_path

    def execute(self, **arguments: Any) -> str:
        """执行文本搜索。"""

        # 校验参数。
        self.validate_arguments(arguments)

        # 读取并清理搜索词。
        query = arguments["query"].strip()

        # 搜索词不能为空。
        if not query:
            raise ToolError("搜索内容不能为空")

        # 读取搜索路径。
        relative_path = arguments.get("path", ".")

        # 读取文件匹配模式。
        file_pattern = arguments.get("file_pattern", "*").strip() or "*"

        # 读取大小写选项。
        case_sensitive = bool(arguments.get("case_sensitive", False))

        # 读取最大结果数量。
        max_results = int(arguments.get("max_results", self.DEFAULT_RESULTS))

        # 限制结果数量范围。
        if max_results < 1 or max_results > self.MAX_RESULTS:
            raise ToolError(f"max_results 必须在 1 到 {self.MAX_RESULTS} 之间")

        # 解析安全搜索路径。
        try:
            target = self.workspace.resolve(relative_path)
        except WorkspaceError as error:
            raise ToolError(str(error)) from error

        # 路径必须存在。
        if not target.exists():
            raise ToolError(f"搜索路径不存在：{relative_path}")

        # 准备比较用的搜索词。
        normalized_query = query if case_sensitive else query.casefold()

        # 保存匹配结果。
        matches: list[str] = []

        # 遍历文件。
        for file_path in self._iter_files(target):
            # 检查文件名模式。
            if not fnmatch(file_path.name, file_pattern):
                continue

            # 跳过过大的文件。
            try:
                if file_path.stat().st_size > self.MAX_FILE_SIZE:
                    continue
                text = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            # 逐行搜索。
            for line_number, line in enumerate(text.splitlines(), start=1):
                # 根据大小写设置比较。
                comparable_line = line if case_sensitive else line.casefold()

                # 不匹配时继续。
                if normalized_query not in comparable_line:
                    continue

                # 生成相对路径。
                relative_file = self.workspace.relative(file_path)

                # 保存匹配行。
                matches.append(f"{relative_file}:{line_number}:{line.strip()}")

                # 达到数量上限后返回。
                if len(matches) >= max_results:
                    matches.append(f"... 结果达到上限 {max_results}，已截断")
                    return "\n".join(matches)

        # 没有匹配时明确说明。
        if not matches:
            return f"未找到包含 {query!r} 的文本"

        # 返回全部结果。
        return "\n".join(matches)
