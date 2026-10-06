"""受限 Git 项目工具。"""

# 导入子进程工具，用于安全调用 Git 命令。
import subprocess

# 导入类型工具。
from typing import Any

# 导入工作目录和异常。
from code_harness.workspace import Workspace, WorkspaceError

# 导入工具基类。
from code_harness.tools.base import BaseTool, ToolError


class BaseGitTool(BaseTool):
    """Git 工具的公共实现。"""

    # 输出最大字符数。
    MAX_OUTPUT_CHARS = 20000

    def __init__(self, workspace: Workspace) -> None:
        """保存工作目录。"""

        # 保存项目安全边界。
        self.workspace = workspace

    def _run_git(self, arguments: list[str]) -> str:
        """在当前工作目录中运行受限 Git 命令。"""

        # 使用参数列表调用 Git，绝不使用 shell=True。
        try:
            result = subprocess.run(
                ["git", "-C", str(self.workspace.root), *arguments],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
                check=False,
            )
        except FileNotFoundError as error:
            raise ToolError("系统中没有找到 Git 命令") from error
        except subprocess.TimeoutExpired as error:
            raise ToolError("Git 命令执行超时") from error

        # 组合标准输出和错误输出。
        output = (result.stdout or result.stderr or "").strip()

        # Git 返回非零状态码时报告错误。
        if result.returncode != 0:
            raise ToolError(f"Git 命令失败：{output or result.returncode}")

        # 限制输出大小。
        if len(output) > self.MAX_OUTPUT_CHARS:
            output = output[: self.MAX_OUTPUT_CHARS] + "\n...（Git 输出已截断）"

        # 空输出使用明确文字。
        return output or "Git 没有返回内容"


class GitStatusTool(BaseGitTool):
    """查看 Git 工作区状态。"""

    # 工具名称。
    name = "git_status"

    # 工具说明。
    description = "查看当前 Git 分支、已修改文件、暂存文件和未跟踪文件。"

    # 不需要参数。
    parameters_schema = {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, **arguments: Any) -> str:
        """执行 git status。"""

        # 校验参数。
        self.validate_arguments(arguments)

        # 返回简洁状态。
        return self._run_git(["status", "--short", "--branch"])


class GitDiffTool(BaseGitTool):
    """查看 Git 代码差异。"""

    # 工具名称。
    name = "git_diff"

    # 工具说明。
    description = "查看工作区或暂存区中的代码差异，可指定单个相对路径。"

    # 参数定义。
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "可选的相对文件或目录路径。",
            },
            "staged": {
                "type": "boolean",
                "description": "是否查看已暂存差异，默认 false。",
            },
        },
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, **arguments: Any) -> str:
        """执行 git diff。"""

        # 校验参数。
        self.validate_arguments(arguments)

        # 判断是否查看暂存区。
        staged = bool(arguments.get("staged", False))

        # 构造基础命令。
        command = ["diff", "--cached"] if staged else ["diff"]

        # 如果指定路径，则限制在 Workspace 内。
        relative_path = arguments.get("path")
        if relative_path:
            # 解析并检查路径。
            try:
                target = self.workspace.resolve(relative_path)
            except WorkspaceError as error:
                raise ToolError(str(error)) from error

            # 使用工作目录相对路径。
            command.extend(["--", self.workspace.relative(target)])

        # 返回差异。
        return self._run_git(command)


class GitLogTool(BaseGitTool):
    """查看 Git 提交历史。"""

    # 工具名称。
    name = "git_log"

    # 工具说明。
    description = "查看最近 Git 提交历史，可指定条数和相对路径。"

    # 参数定义。
    parameters_schema = {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "最多显示多少条提交，默认 10，最大 50。",
            },
            "path": {
                "type": "string",
                "description": "可选的相对文件或目录路径。",
            },
        },
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, **arguments: Any) -> str:
        """执行 git log。"""

        # 校验参数。
        self.validate_arguments(arguments)

        # 读取提交数量。
        limit = int(arguments.get("limit", 10))

        # 限制提交数量。
        if limit < 1 or limit > 50:
            raise ToolError("limit 必须在 1 到 50 之间")

        # 构造基础命令。
        command = ["log", "--oneline", "--decorate", "-n", str(limit)]

        # 如果指定路径，则限制在 Workspace 内。
        relative_path = arguments.get("path")
        if relative_path:
            # 解析并检查路径。
            try:
                target = self.workspace.resolve(relative_path)
            except WorkspaceError as error:
                raise ToolError(str(error)) from error

            # 只查看该路径的提交。
            command.extend(["--", self.workspace.relative(target)])

        # 返回历史。
        return self._run_git(command)
