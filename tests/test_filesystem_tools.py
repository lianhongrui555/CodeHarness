"""测试只读文件系统工具。"""

# 导入路径工具。
from pathlib import Path

# 导入 pytest。
import pytest

# 导入工具。
from code_harness.tools.filesystem import ListFilesTool, ReadFileTool
from code_harness.tools.base import ToolError

# 导入工作目录。
from code_harness.workspace import Workspace, WorkspaceError


def create_workspace(tmp_path: Path) -> Workspace:
    """创建测试项目目录。"""

    # 创建目录和文件。
    (tmp_path / "src").mkdir()
    (tmp_path / ".venv").mkdir()
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("第一行\n第二行\n第三行\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=bad\n", encoding="utf-8")

    # 返回工作目录。
    return Workspace(tmp_path)


def test_workspace_blocks_escape_and_sensitive_paths(tmp_path: Path) -> None:
    """工作目录必须阻止越界和敏感文件访问。"""

    # 创建测试目录。
    workspace = create_workspace(tmp_path)

    # 阻止 ../ 越界。
    with pytest.raises(WorkspaceError, match="超出工作目录"):
        workspace.resolve("../outside.txt")

    # 阻止绝对路径。
    with pytest.raises(WorkspaceError, match="相对路径"):
        workspace.resolve("C:/Windows/win.ini")

    # 阻止 .env。
    with pytest.raises(WorkspaceError, match="敏感路径"):
        workspace.resolve(".env")


def test_list_files_non_recursive_and_recursive(tmp_path: Path) -> None:
    """目录工具应列出文件，并过滤敏感文件。"""

    # 创建工具。
    tool = ListFilesTool(create_workspace(tmp_path))

    # 普通列表。
    result = tool.execute(path=".")

    # 验证排序和敏感过滤。
    assert "d src" in result
    assert "f README.md" in result
    assert ".env" not in result
    assert ".venv" not in result
    assert "node_modules" not in result

    # 递归列表。
    recursive_result = tool.execute(path=".", recursive=True)
    assert "f src/main.py" in recursive_result


def test_read_file_with_line_range(tmp_path: Path) -> None:
    """文件读取工具应支持行范围。"""

    # 创建工具。
    tool = ReadFileTool(create_workspace(tmp_path))

    # 读取第二行到第三行。
    result = tool.execute(path="README.md", start_line=2, max_lines=2)

    # 验证输出。
    assert "第 2-3 行，共 3 行" in result
    assert "2 | 第二行" in result
    assert "3 | 第三行" in result
    assert "第一行" not in result


def test_read_file_rejects_missing_and_sensitive_files(tmp_path: Path) -> None:
    """文件读取工具应拒绝不存在和敏感文件。"""

    # 创建工具。
    tool = ReadFileTool(create_workspace(tmp_path))

    # 拒绝不存在文件。
    with pytest.raises(ToolError, match="文件不存在"):
        tool.execute(path="missing.txt")

    # 拒绝 .env。
    with pytest.raises(ToolError, match="敏感路径"):
        tool.execute(path=".env")
