"""测试代码文本搜索工具。"""

# 导入路径工具。
from pathlib import Path

# 导入 pytest。
import pytest

# 导入搜索工具。
from code_harness.tools.base import ToolError
from code_harness.tools.search import SearchTextTool

# 导入工作目录。
from code_harness.workspace import Workspace


def create_workspace(tmp_path: Path) -> Workspace:
    """创建搜索测试目录。"""

    # 创建源码目录。
    source = tmp_path / "src"
    source.mkdir()

    # 创建 Python 文件。
    (source / "calculator.py").write_text(
        "class CalculatorTool:\n    name = 'calculator'\n",
        encoding="utf-8",
    )

    # 创建文本文件。
    (tmp_path / "README.md").write_text(
        "CodeHarness CalculatorTool 使用说明\n",
        encoding="utf-8",
    )

    # 创建敏感文件和缓存目录。
    (tmp_path / ".env").write_text("CalculatorTool=secret\n", encoding="utf-8")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "hidden.py").write_text("CalculatorTool\n", encoding="utf-8")

    # 返回工作目录。
    return Workspace(tmp_path)


def test_search_text_finds_multiple_file_types(tmp_path: Path) -> None:
    """搜索应返回路径、行号和匹配内容。"""

    # 创建搜索工具。
    tool = SearchTextTool(create_workspace(tmp_path))

    # 搜索名称。
    result = tool.execute(query="CalculatorTool")

    # 验证 Python 和 Markdown 结果。
    assert "src/calculator.py:1:class CalculatorTool:" in result
    assert "README.md:1:CodeHarness CalculatorTool 使用说明" in result

    # 敏感文件和缓存目录必须被忽略。
    assert ".env" not in result
    assert "__pycache__" not in result


def test_search_text_case_and_pattern(tmp_path: Path) -> None:
    """搜索应支持大小写和文件名模式。"""

    # 创建搜索工具。
    tool = SearchTextTool(create_workspace(tmp_path))

    # 小写搜索默认不区分大小写。
    assert "calculator.py" in tool.execute(query="calculatortool")

    # 只搜索 Python 文件。
    python_result = tool.execute(query="CalculatorTool", file_pattern="*.py")
    assert "README.md" not in python_result
    assert "src/calculator.py" in python_result


def test_search_text_no_match_and_bad_arguments(tmp_path: Path) -> None:
    """搜索应正确处理空结果和非法参数。"""

    # 创建搜索工具。
    tool = SearchTextTool(create_workspace(tmp_path))

    # 无匹配结果。
    assert "未找到" in tool.execute(query="NotExistKeyword")

    # 空搜索词。
    with pytest.raises(ToolError, match="不能为空"):
        tool.execute(query="")

    # 超出结果上限。
    with pytest.raises(ToolError, match="max_results"):
        tool.execute(query="CalculatorTool", max_results=999)
