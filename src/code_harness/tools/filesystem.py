"""只读文件系统工具。"""

# 导入操作系统接口。
import os

# 导入路径类型。
from pathlib import Path

# 导入类型工具。
from typing import Any, Iterator

# 导入工作目录和异常。
from code_harness.workspace import Workspace, WorkspaceError

# 导入工具基类。
from code_harness.tools.base import BaseTool, ToolError


class ListFilesTool(BaseTool):
    """列出工作目录内的文件和文件夹。"""

    # 工具名称。
    name = "list_files"

    # 工具说明。
    description = "列出代码项目中的文件和目录，只能访问指定工作目录内部。"

    # 参数定义。
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "相对工作目录的路径，默认为 .。",
            },
            "recursive": {
                "type": "boolean",
                "description": "是否递归列出子目录，默认 false。",
            },
        },
        "required": [],
        "additionalProperties": False,
    }

    # 最多返回的条目数量。
    MAX_ENTRIES = 200

    def __init__(self, workspace: Workspace) -> None:
        """保存工作目录。"""

        # 保存工作目录对象。
        self.workspace = workspace

    def _iter_recursive(self, directory: Path) -> Iterator[Path]:
        """安全地递归遍历目录。"""

        # 对每层目录排序，保证输出稳定。
        for current_root, directory_names, file_names in os.walk(directory):
            # 过滤敏感目录。
            directory_names[:] = sorted(
                name
                for name in directory_names
                if not self.workspace.is_sensitive(Path(current_root) / name) and not self.workspace.is_ignored(Path(current_root) / name)
            )

            # 生成当前目录下的文件。
            for file_name in sorted(file_names):
                file_path = Path(current_root) / file_name
                if not self.workspace.is_sensitive(file_path) and not self.workspace.is_ignored(file_path):
                    yield file_path

            # 生成下一层目录。
            for directory_name in directory_names:
                yield Path(current_root) / directory_name

    def execute(self, **arguments: Any) -> str:
        """执行目录列表。"""

        # 校验参数。
        self.validate_arguments(arguments)

        # 读取相对路径。
        relative_path = arguments.get("path", ".")

        # 读取递归选项。
        recursive = bool(arguments.get("recursive", False))

        # 使用 try 把路径错误转换成工具错误。
        try:
            # 解析安全路径。
            directory = self.workspace.resolve(relative_path)
        except WorkspaceError as error:
            raise ToolError(str(error)) from error

        # 目标必须是目录。
        if not directory.is_dir():
            raise ToolError(f"目录不存在：{relative_path}")

        # 选择普通列表或递归列表。
        if recursive:
            entries = self._iter_recursive(directory)
        else:
            entries = iter(sorted((item for item in directory.iterdir() if not self.workspace.is_ignored(item)), key=lambda item: (item.is_file(), item.name.lower())))

        # 保存输出行。
        lines: list[str] = []

        # 最多读取限制数量的条目。
        for entry in entries:
            # 过滤敏感路径。
            try:
                if self.workspace.is_sensitive(entry):
                    continue
                display_path = self.workspace.relative(entry)
            except (ValueError, WorkspaceError):
                continue

            # 目录使用 d，文件使用 f。
            prefix = "d" if entry.is_dir() else "f"
            lines.append(f"{prefix} {display_path}")

            # 达到限制后停止。
            if len(lines) >= self.MAX_ENTRIES:
                lines.append(f"... 结果超过 {self.MAX_ENTRIES} 条，已截断")
                break

        # 空目录返回明确提示。
        if not lines:
            return f"目录 {relative_path} 为空"

        # 返回列表文本。
        return "\n".join(lines)


class ReadFileTool(BaseTool):
    """读取 UTF-8 文本文件。"""

    # 工具名称。
    name = "read_file"

    # 工具说明。
    description = "读取代码项目中的 UTF-8 文本文件，支持指定起始行和最大行数。"

    # 参数定义。
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "相对工作目录的文件路径。",
            },
            "start_line": {
                "type": "integer",
                "description": "起始行号，从 1 开始，默认 1。",
            },
            "max_lines": {
                "type": "integer",
                "description": "最多读取行数，默认 200，最大 400。",
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    }

    # 最大文件大小：512 KB。
    MAX_FILE_SIZE = 512 * 1024

    # 默认读取行数。
    DEFAULT_LINES = 200

    # 最大读取行数。
    MAX_LINES = 400

    def __init__(self, workspace: Workspace) -> None:
        """保存工作目录。"""

        # 保存工作目录对象。
        self.workspace = workspace

    def execute(self, **arguments: Any) -> str:
        """读取文件内容。"""

        # 校验参数。
        self.validate_arguments(arguments)

        # 读取路径。
        relative_path = arguments["path"]

        # 读取起始行。
        start_line = int(arguments.get("start_line", 1))

        # 读取最大行数。
        max_lines = int(arguments.get("max_lines", self.DEFAULT_LINES))

        # 起始行必须大于等于 1。
        if start_line < 1:
            raise ToolError("start_line 必须大于等于 1")

        # 限制最大行数范围。
        if max_lines < 1 or max_lines > self.MAX_LINES:
            raise ToolError(f"max_lines 必须在 1 到 {self.MAX_LINES} 之间")

        # 使用 try 解析安全路径。
        try:
            file_path = self.workspace.resolve(relative_path)
        except WorkspaceError as error:
            raise ToolError(str(error)) from error

        # 文件必须存在。
        if not file_path.is_file():
            raise ToolError(f"文件不存在：{relative_path}")

        # 检查文件大小。
        size = file_path.stat().st_size
        if size > self.MAX_FILE_SIZE:
            raise ToolError(f"文件超过 {self.MAX_FILE_SIZE} 字节，拒绝直接读取")

        # 使用 try 读取 UTF-8 文本。
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise ToolError(f"文件不是有效 UTF-8 文本：{relative_path}") from error
        except OSError as error:
            raise ToolError(f"读取文件失败：{error}") from error

        # 拆分所有行。
        lines = text.splitlines()

        # 计算切片边界。
        start_index = start_line - 1
        end_index = min(start_index + max_lines, len(lines))

        # 准备带行号的结果。
        numbered_lines = [
            f"{number:>4} | {lines[number - 1]}"
            for number in range(start_line, end_index + 1)
        ]

        # 处理空文件或超出范围。
        if not numbered_lines:
            return f"文件 {relative_path} 在指定行范围内没有内容"

        # 添加文件信息。
        header = f"文件：{relative_path}（第 {start_line}-{end_index} 行，共 {len(lines)} 行）"

        # 返回完整结果。
        return header + "\n" + "\n".join(numbered_lines)
