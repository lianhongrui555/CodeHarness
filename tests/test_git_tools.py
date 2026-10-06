"""测试受限 Git 工具。"""

# 导入子进程工具。
import subprocess

# 导入路径工具。
from pathlib import Path

# 导入 pytest。
import pytest

# 导入 Git 工具和异常。
from code_harness.tools.base import ToolError
from code_harness.tools.git_tools import GitDiffTool, GitLogTool, GitStatusTool

# 导入工作目录。
from code_harness.workspace import Workspace


def run_git(repo: Path, *arguments: str) -> None:
    """执行测试 Git 命令。"""

    # 设置匿名提交环境，避免依赖全局配置。
    environment = {
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }

    # 运行 Git 命令。
    subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, **environment},
    )


def create_repo(tmp_path: Path) -> Workspace:
    """创建带初始提交的测试仓库。"""

    # 初始化仓库。
    run_git(tmp_path, "init", "-b", "main")

    # 创建并提交文件。
    (tmp_path / "hello.py").write_text("print('hello')\n", encoding="utf-8")
    run_git(tmp_path, "add", "hello.py")
    run_git(tmp_path, "commit", "-m", "initial commit")

    # 返回工作目录。
    return Workspace(tmp_path)


def test_git_status_and_diff(tmp_path: Path) -> None:
    """状态和差异工具应反映真实工作区变化。"""

    # 创建仓库并修改文件。
    workspace = create_repo(tmp_path)
    (tmp_path / "hello.py").write_text("print('hello world')\n", encoding="utf-8")
    (tmp_path / "new.txt").write_text("new\n", encoding="utf-8")

    # 查看状态。
    status = GitStatusTool(workspace).execute()

    # 验证已修改和未跟踪文件。
    assert "main" in status
    assert "hello.py" in status
    assert "?? new.txt" in status

    # 查看指定文件差异。
    diff = GitDiffTool(workspace).execute(path="hello.py")

    # 验证差异内容。
    assert "hello world" in diff


def test_git_log_and_path_validation(tmp_path: Path) -> None:
    """提交历史应正常返回，越界路径必须拒绝。"""

    # 创建仓库。
    workspace = create_repo(tmp_path)

    # 查看提交历史。
    log = GitLogTool(workspace).execute(limit=5)

    # 验证提交信息。
    assert "initial commit" in log

    # 拒绝目录穿越。
    with pytest.raises(ToolError, match="超出工作目录"):
        GitDiffTool(workspace).execute(path="../outside.txt")
